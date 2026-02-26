from __future__ import annotations

import subprocess
from dataclasses import replace
from typing import List

from PySide6.QtCore import QObject, QTimer, Signal

from loginvrcast.core.settings_store import SettingsStore
from loginvrcast.core.state import DeviceInfo, AdbStatus
from loginvrcast.tools.adb_locator import find_adb
from loginvrcast.ui.widgets import app_dir_for_user_files


class AdbMonitor(QObject):
    devices_changed = Signal(list)        # list[DeviceInfo]
    adb_status_changed = Signal(object)   # AdbStatus

    def __init__(self, settings_store: SettingsStore):
        super().__init__()
        self._settings_store = settings_store
        self._timer = QTimer(self)
        self._timer.setInterval(3000)  # CPU-light
        self._timer.timeout.connect(self.refresh)

        self._adb: AdbStatus | None = None
        self._devices: list[DeviceInfo] = []
        self._selected_serial: str | None = None
        self._model_cache: dict[str, str] = {}

    def start(self) -> None:
        self.refresh()
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

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