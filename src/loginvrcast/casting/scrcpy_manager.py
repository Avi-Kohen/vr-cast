from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from loginvrcast.core.settings_store import SettingsStore
from loginvrcast.tools.scrcpy_locator import scrcpy_path_for_current_os
from loginvrcast.casting.command_builder import build_scrcpy_args


class ScrcpyManager(QObject):
    started = Signal()
    stopped = Signal()
    error = Signal(str)

    def __init__(self, settings_store: SettingsStore):
        super().__init__()
        self._settings_store = settings_store
        self._proc: subprocess.Popen | None = None

    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def start(self, adb_path: str, serial: str | None) -> None:
        if self.is_running():
            return

        scrcpy = scrcpy_path_for_current_os()
        if not scrcpy.exists():
            self.error.emit(f"Bundled scrcpy not found: {scrcpy}")
            return

        args = [str(scrcpy)]
        # v1: single device - if serial exists, pass it
        if serial:
            args += ["--serial", serial]

        args += build_scrcpy_args(self._settings_store.settings)

        env = os.environ.copy()
        env["ADB"] = adb_path  # scrcpy uses this

        try:
            creationflags = 0
            if sys.platform.startswith("win"):
                creationflags = subprocess.CREATE_NO_WINDOW

            self._proc = subprocess.Popen(
                args,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=creationflags,
            )
            self.started.emit()
        except Exception as e:
            self._proc = None
            self.error.emit(str(e))

    def stop(self) -> None:
        if not self.is_running():
            self._proc = None
            return
        try:
            if self._proc is not None:
                self._proc.terminate()
        except Exception:
            pass
        self._proc = None
        self.stopped.emit()