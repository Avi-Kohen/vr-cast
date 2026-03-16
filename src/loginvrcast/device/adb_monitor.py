from __future__ import annotations

import re
import time
from dataclasses import replace

from PySide6.QtCore import QObject, QTimer, Signal, QRunnable, QThreadPool

from loginvrcast.core.settings_store import SettingsStore
from loginvrcast.core.wifi import parse_wifi_endpoint, extract_ipv4
from loginvrcast.core.wifi_runtime import build_wifi_plan, execute_wifi_plan, apply_manual_connect_policy
from loginvrcast.core.state import DeviceInfo, AdbStatus
from loginvrcast.tools.adb_locator import find_adb
from loginvrcast.tools.subprocess_utils import run_quiet
from loginvrcast.ui.widgets import app_dir_for_user_files


class _PollSignals(QObject):
    done = Signal(list, str, str)   # devices, selected_serial, selected_model
    failed = Signal(str)


class _AdbPollTask(QRunnable):
    def __init__(self, adb_path: str, selected_serial: str | None):
        super().__init__()
        self.adb_path = adb_path
        self.selected_serial = selected_serial
        self.signals = _PollSignals()

    def run(self) -> None:
        try:
            cp = run_quiet([self.adb_path, "devices", "-l"], timeout=2)
            lines = [ln.strip() for ln in cp.stdout.splitlines() if ln.strip()]

            devices: list[DeviceInfo] = []
            for ln in lines[1:]:
                parts = ln.split()
                if len(parts) < 2:
                    continue
                serial = parts[0]
                state = parts[1]
                model = None
                for p in parts[2:]:
                    if p.startswith("model:"):
                        model = p.split("model:", 1)[1]
                        break
                devices.append(DeviceInfo(serial=serial, adb_state=state, model=model))

            chosen_serial = self.selected_serial
            serials = {d.serial for d in devices}
            if not chosen_serial or chosen_serial not in serials:
                chosen_serial = devices[0].serial if devices else ""

            chosen_model = ""
            if chosen_serial:
                d = next((x for x in devices if x.serial == chosen_serial), None)
                if d and d.adb_state == "device" and not d.model:
                    cp2 = run_quiet(
                        [self.adb_path, "-s", chosen_serial, "shell", "getprop", "ro.product.model"],
                        timeout=2,
                    )
                    chosen_model = (cp2.stdout or "").strip()
                elif d and d.model:
                    chosen_model = d.model

            self.signals.done.emit(devices, chosen_serial, chosen_model)
        except Exception as e:
            self.signals.failed.emit(str(e))


class AdbMonitor(QObject):
    devices_changed = Signal(list)
    adb_status_changed = Signal(object)
    wifi_status_changed = Signal(str)

    def __init__(self, settings_store: SettingsStore, wifi_enabled: bool):
        super().__init__()
        self._settings_store = settings_store
        self._wifi_enabled = wifi_enabled

        self._timer = QTimer(self)
        self._timer.setInterval(3000)
        self._timer.timeout.connect(self.refresh)

        self._pool = QThreadPool.globalInstance()
        self._poll_inflight = False
        self._poll_pending = False
        self._poll_seq = 0
        self._current_task = None

        self._adb: AdbStatus | None = None
        self._devices: list[DeviceInfo] = []
        self._selected_serial: str | None = None
        self._model_cache: dict[str, str] = {}

        self._last_tcpip_attempt = 0.0
        self._last_connect_attempt = 0.0
        self._wifi_status = ""
        self._manual_connect_requested = False

    def start(self) -> None:
        self.refresh()
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def _start_poll(self, adb_path: str) -> None:
        self._poll_inflight = True
        self._poll_pending = False
        self._poll_seq += 1
        seq = self._poll_seq

        task = _AdbPollTask(adb_path, self._selected_serial)
        self._current_task = task

        task.signals.done.connect(
            lambda devices, selected_serial, selected_model, seq=seq:
            self._on_poll_done(seq, devices, selected_serial, selected_model)
        )
        task.signals.failed.connect(lambda msg, seq=seq: self._on_poll_failed(seq, msg))
        self._pool.start(task)

    def _on_poll_done(self, seq: int, devices: list, selected_serial: str, selected_model: str) -> None:
        if seq != self._poll_seq:
            return

        self._poll_inflight = False
        self._current_task = None
        self._devices = list(devices)

        serials = {d.serial for d in self._devices}
        if self._selected_serial in serials:
            chosen = self._selected_serial
        elif selected_serial in serials:
            chosen = selected_serial
        else:
            chosen = self._devices[0].serial if self._devices else None

        self._selected_serial = chosen

        if chosen and selected_model:
            self._model_cache[chosen] = selected_model
            self._apply_model(chosen, selected_model)

        self.devices_changed.emit(self._devices)

        if self._poll_pending and self._adb and self._adb.ok and self._adb.adb_path:
            self._start_poll(self._adb.adb_path)

    def _on_poll_failed(self, seq: int, _msg: str) -> None:
        if seq != self._poll_seq:
            return

        self._poll_inflight = False
        self._current_task = None

        if self._devices:
            self._devices = []
            self._selected_serial = None
            self.devices_changed.emit(self._devices)

        if self._poll_pending and self._adb and self._adb.ok and self._adb.adb_path:
            self._start_poll(self._adb.adb_path)


    def _set_wifi_status(self, msg: str) -> None:
        if msg != self._wifi_status:
            self._wifi_status = msg
            self.wifi_status_changed.emit(msg)

    def connect_wifi_now(self) -> None:
        adb = self._adb
        if not adb or not adb.ok or not adb.adb_path:
            self._set_wifi_status("Wi-Fi: ADB not ready")
            return
        self._manual_connect_requested = True
        self._last_connect_attempt = 0.0
        self._last_tcpip_attempt = 0.0
        self._maybe_prepare_wifi(adb.adb_path)
        self.refresh()

    def disconnect_wifi_now(self) -> None:
        adb = self._adb
        settings = self._settings_store.settings
        if not adb or not adb.ok or not adb.adb_path:
            self._set_wifi_status("Wi-Fi: ADB not ready")
            return

        endpoint, _ = self._effective_wifi_endpoint(adb.adb_path, settings.wifi_endpoint.strip(), self._devices)
        host, port = parse_wifi_endpoint(endpoint)
        if not host:
            self._set_wifi_status("Wi-Fi: set endpoint or connect USB once for auto-detect")
            return

        self._manual_connect_requested = False
        try:
            cp = run_quiet([adb.adb_path, "disconnect", f"{host}:{port}"], timeout=3)
            out = (cp.stdout or "").strip()
            self._set_wifi_status(f"Wi-Fi: {out or 'disconnected'}")
        except Exception as e:
            self._set_wifi_status(f"Wi-Fi: disconnect failed ({e})")

    def refresh(self) -> None:
        app_dir = app_dir_for_user_files()
        adb = find_adb(self._settings_store.settings.platform_tools_dir, app_dir)

        if (
            self._adb is None
            or adb.ok != self._adb.ok
            or adb.adb_path != self._adb.adb_path
            or adb.message != self._adb.message
        ):
            self._adb = adb
            self.adb_status_changed.emit(adb)

        if not adb.ok or not adb.adb_path:
            self._poll_seq += 1
            self._poll_pending = False

            if self._devices:
                self._devices = []
                self._selected_serial = None
                self.devices_changed.emit(self._devices)
            return

        self._maybe_prepare_wifi(adb.adb_path)

        if self._poll_inflight:
            self._poll_pending = True
            return

        self._start_poll(adb.adb_path)

    def _discover_usb_wifi_endpoint(self, adb_path: str, devices: list[DeviceInfo]) -> str:
        usb_ready = next((d for d in devices if d.adb_state == "device" and ":" not in d.serial), None)
        if not usb_ready:
            return ""

        try:
            cp = run_quiet([adb_path, "-s", usb_ready.serial, "shell", "ip", "route"], timeout=3)
            route_text = cp.stdout or ""
            src_match = re.search(r"src\s+((?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3})", route_text)
            ip = src_match.group(1) if src_match else extract_ipv4(route_text)
            if ip:
                return f"{ip}:5555"
        except Exception:
            pass

        try:
            cp = run_quiet(
                [adb_path, "-s", usb_ready.serial, "shell", "getprop", "dhcp.wlan0.ipaddress"],
                timeout=3,
            )
            ip = extract_ipv4((cp.stdout or "").strip())
            if ip:
                return f"{ip}:5555"
        except Exception:
            pass

        return ""

    def _effective_wifi_endpoint(self, adb_path: str, settings_endpoint: str, devices: list[DeviceInfo]) -> tuple[str, bool]:
        endpoint = settings_endpoint.strip()
        if endpoint:
            return endpoint, False

        discovered = self._discover_usb_wifi_endpoint(adb_path, devices)
        if discovered:
            return discovered, True
        return "", True

    def _maybe_prepare_wifi(self, adb_path: str) -> None:
        settings = self._settings_store.settings
        now = time.monotonic()
        devices = list(self._devices)
        endpoint, auto_detected = self._effective_wifi_endpoint(adb_path, settings.wifi_endpoint.strip(), devices)

        plan = build_wifi_plan(
            wifi_enabled=self._wifi_enabled,
            connection_mode=settings.connection_mode,
            endpoint=endpoint,
            devices=devices,
            now_s=now,
            last_tcpip_attempt_s=self._last_tcpip_attempt,
            last_connect_attempt_s=self._last_connect_attempt,
        )

        if not plan.status:
            self._set_wifi_status("")
            return

        self._set_wifi_status(f"Wi-Fi: auto endpoint {endpoint}" if auto_detected and endpoint else plan.status)
        should_execute, gated_status = apply_manual_connect_policy(
            manual_connect_requested=self._manual_connect_requested,
            plan_status=plan.status,
            target=plan.target,
        )
        self._set_wifi_status(gated_status)
        if not should_execute:
            return

        result = execute_wifi_plan(
            plan=plan,
            adb_path=adb_path,
            endpoint=endpoint,
            devices=devices,
            now_s=now,
            last_tcpip_attempt_s=self._last_tcpip_attempt,
            last_connect_attempt_s=self._last_connect_attempt,
            run_cmd=lambda cmd: (run_quiet(cmd, timeout=3).stdout or "").strip(),
        )

        self._manual_connect_requested = False
        self._last_tcpip_attempt = result.tcpip_attempt_s
        self._last_connect_attempt = result.connect_attempt_s
        self._set_wifi_status(result.status)


    def set_selected_serial(self, serial: str | None) -> None:
        self._selected_serial = serial
        self.refresh()

    def selected_serial(self) -> str | None:
        return self._selected_serial

    def _apply_model(self, serial: str, model: str) -> None:
        new_list: list[DeviceInfo] = []
        for d in self._devices:
            if d.serial == serial:
                new_list.append(replace(d, model=model))
            else:
                new_list.append(d)
        self._devices = new_list
