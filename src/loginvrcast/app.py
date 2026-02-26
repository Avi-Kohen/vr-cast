from __future__ import annotations

from PySide6.QtWidgets import QApplication

from loginvrcast.core.settings_store import SettingsStore
from loginvrcast.device.adb_monitor import AdbMonitor
from loginvrcast.casting.scrcpy_manager import ScrcpyManager
from loginvrcast.ui.main_window import MainWindow


def main() -> int:
    app = QApplication([])

    settings = SettingsStore.load()
    monitor = AdbMonitor(settings_store=settings)
    scrcpy = ScrcpyManager(settings_store=settings)

    win = MainWindow(settings_store=settings, adb_monitor=monitor, scrcpy_manager=scrcpy)
    win.show()

    monitor.start()  # 3s polling
    return app.exec()