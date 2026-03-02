from __future__ import annotations

import time
from dataclasses import replace

from PySide6.QtCore import QObject, QTimer, Signal, QRunnable, QThreadPool

from loginvrcast.core.settings_store import SettingsStore
from loginvrcast.core.wifi import parse_wifi_endpoint
from loginvrcast.core.wifi_runtime import build_wifi_plan
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

        host, port = parse_wifi_endpoint(settings.wifi_endpoint.strip())
        if not host:
            self._set_wifi_status("Wi-Fi: set endpoint (ip[:port])")
            return

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

    def _maybe_prepare_wifi(self, adb_path: str) -> None:
        settings = self._settings_store.settings
        now = time.monotonic()
        devices = self._run_devices(adb_path)

        plan = build_wifi_plan(
            wifi_enabled=self._wifi_enabled,
            connection_mode=settings.connection_mode,
            endpoint=settings.wifi_endpoint.strip(),
            devices=devices,
            now_s=now,
            last_tcpip_attempt_s=self._last_tcpip_attempt,
            last_connect_attempt_s=self._last_connect_attempt,
        )

        if not plan.status:
            self._set_wifi_status("")
            return

        self._set_wifi_status(plan.status)
        if not plan.target:
            return

        if plan.should_tcpip:
            usb_ready = next((d for d in devices if d.adb_state == "device" and ":" not in d.serial), None)
            if usb_ready:
                self._last_tcpip_attempt = now
                try:
                    _, port = parse_wifi_endpoint(settings.wifi_endpoint.strip())
                    run_quiet([adb_path, "-s", usb_ready.serial, "tcpip", str(port)], timeout=3)
                    self._set_wifi_status(f"Wi-Fi: enabled tcpip:{port} via USB")
                except Exception as e:
                    self._set_wifi_status(f"Wi-Fi: tcpip failed ({e})")

        if plan.should_connect:
            self._last_connect_attempt = now
            try:
                cp = run_quiet([adb_path, "connect", plan.target], timeout=3)
                out = (cp.stdout or "").strip()
                self._set_wifi_status(f"Wi-Fi: {out or 'connect attempted'}")
            except Exception as e:
                self._set_wifi_status(f"Wi-Fi: connect failed ({e})")


    def set_selected_serial(self, serial: str | None) -> None:
        self._selected_serial = serial
        self.refresh()

    def selected_serial(self) -> str | None:
        return self._selected_serial

    def _run_devices(self, adb_path: str) -> list[DeviceInfo]:
        try:
            cp = run_quiet([adb_path, "devices", "-l"], timeout=2)
        except Exception:
            return []

        lines = [ln.strip() for ln in (cp.stdout or "").splitlines() if ln.strip()]
        out: list[DeviceInfo] = []
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
            out.append(DeviceInfo(serial=serial, adb_state=state, model=model))
        return out

    def _apply_model(self, serial: str, model: str) -> None:
        new_list: list[DeviceInfo] = []
        for d in self._devices:
            if d.serial == serial:
                new_list.append(replace(d, model=model))
            else:
                new_list.append(d)
        self._devices = new_list
