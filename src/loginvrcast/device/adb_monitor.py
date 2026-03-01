from __future__ import annotations

import subprocess
from dataclasses import replace, dataclass
from typing import List

from PySide6.QtCore import QObject, QTimer, Signal, QRunnable, QThreadPool
from loginvrcast.core.settings_store import SettingsStore
from loginvrcast.core.state import DeviceInfo, AdbStatus
from loginvrcast.tools.adb_locator import find_adb
from loginvrcast.ui.widgets import app_dir_for_user_files
from loginvrcast.tools.subprocess_utils import run_quiet


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
            # 1) adb devices -l
            cp = run_quiet([self.adb_path, "devices", "-l"], timeout=2)
            lines = [ln.strip() for ln in cp.stdout.splitlines() if ln.strip()]

            devices: list[DeviceInfo] = []
            for ln in lines[1:]:  # skip header
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

            # 2) choose selected (v1 default = first)
            chosen_serial = self.selected_serial
            serials = {d.serial for d in devices}
            if not chosen_serial or chosen_serial not in serials:
                chosen_serial = devices[0].serial if devices else ""

            # 3) fetch model only for selected + only if authorized + missing
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
    devices_changed = Signal(list)        # list[DeviceInfo]
    adb_status_changed = Signal(object)   # AdbStatus

    def __init__(self, settings_store: SettingsStore):
        super().__init__()
        self._settings_store = settings_store
        self._timer = QTimer(self)
        self._timer.setInterval(3000)  # CPU-light
        self._timer.timeout.connect(self.refresh)

        self._pool = QThreadPool.globalInstance()
        self._poll_inflight = False

        self._adb: AdbStatus | None = None
        self._devices: list[DeviceInfo] = []
        self._selected_serial: str | None = None
        self._model_cache: dict[str, str] = {}

    def start(self) -> None:
        self.refresh()
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()
    
    def _on_poll_done(self, devices: list, selected_serial: str, selected_model: str) -> None:
        self._poll_inflight = False
        self._devices = list(devices)

        # default selection = first detected, but don’t fight user while it exists
        self._selected_serial = selected_serial or None

    # apply model only for selected
        if self._selected_serial and selected_model:
            self._model_cache[self._selected_serial] = selected_model
            self._apply_model(self._selected_serial, selected_model)

        self.devices_changed.emit(self._devices)

    def _on_poll_failed(self, msg: str) -> None:
        self._poll_inflight = False
        # keep it simple: don’t crash; just clear list
        self._devices = []
        self.devices_changed.emit(self._devices)
        
        
    def refresh(self) -> None:
        app_dir = app_dir_for_user_files()
        adb = find_adb(self._settings_store.settings.platform_tools_dir, app_dir)
        if (self._adb is None) or (adb.ok != self._adb.ok) or (adb.adb_path != self._adb.adb_path) or (adb.message != self._adb.message):
            self._adb = adb
            self.adb_status_changed.emit(adb)

        if not adb.ok or not adb.adb_path:
            self._devices = []
            self.devices_changed.emit(self._devices)
            return
        if self._poll_inflight:
            return  # skip if previous poll still running (should be rare, but just in case)  
        
        self._poll_inflight = True
        task = _AdbPollTask(adb.adb_path, self._selected_serial)
        task.signals.done.connect(self._on_poll_done)
        task.signals.failed.connect(self._on_poll_failed)
        self._pool.start(task)
        
        # Get device list
        devices = self._run_devices(adb.adb_path)
        self._devices = devices

        # Default selection: first detected device
        if devices:
            if self._selected_serial not in {d.serial for d in devices}:
                self._selected_serial = devices[0].serial
        else:
            self._selected_serial = None

        # Enrich model only for selected device (CPU-light)
        if self._selected_serial:
            self._maybe_fetch_model(adb.adb_path, self._selected_serial)

        # Emit updated list
        self.devices_changed.emit(self._devices)

    def set_selected_serial(self, serial: str | None) -> None:
        self._selected_serial = serial
        # refresh immediately on selection (still CPU-light)
        self.refresh()

    def selected_serial(self) -> str | None:
        return self._selected_serial

    def adb_status(self) -> AdbStatus | None:
        return self._adb

    def devices(self) -> list[DeviceInfo]:
        return self._devices

    def _run_devices(self, adb_path: str) -> list[DeviceInfo]:
        try:
            cp = subprocess.run([adb_path, "devices", "-l"], capture_output=True, text=True, timeout=2, check=True)
        except Exception:
            return []

        lines = [ln.strip() for ln in cp.stdout.splitlines() if ln.strip()]
        out: list[DeviceInfo] = []
        for ln in lines[1:]:  # skip header "List of devices attached"
            parts = ln.split()
            if not parts:
                continue
            serial = parts[0]
            state = parts[1] if len(parts) > 1 else "unknown"
            model = None
            for p in parts[2:]:
                if p.startswith("model:"):
                    model = p.split("model:", 1)[1]
                    break
            out.append(DeviceInfo(serial=serial, adb_state=state, model=model))
        return out

    def _maybe_fetch_model(self, adb_path: str, serial: str) -> None:
        if serial in self._model_cache:
            self._apply_model(serial, self._model_cache[serial])
            return

        # Find the device entry
        idx = next((i for i, d in enumerate(self._devices) if d.serial == serial), None)
        if idx is None:
            return
        d = self._devices[idx]
        if d.adb_state != "device":
            return
        if d.model:
            self._model_cache[serial] = d.model
            return

        try:
            cp = subprocess.run(
                [adb_path, "-s", serial, "shell", "getprop", "ro.product.model"],
                capture_output=True,
                text=True,
                timeout=2,
                check=True,
            )
            model = cp.stdout.strip() or "Unknown"
        except Exception:
            model = "Unknown"

        self._model_cache[serial] = model
        self._apply_model(serial, model)

    def _apply_model(self, serial: str, model: str) -> None:
        # Update in list immutably
        new_list: list[DeviceInfo] = []
        for d in self._devices:
            if d.serial == serial:
                new_list.append(replace(d, model=model))
            else:
                new_list.append(d)
        self._devices = new_list