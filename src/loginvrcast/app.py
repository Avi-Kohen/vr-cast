from __future__ import annotations
import sys
from typing import Any

from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from loginvrcast.core.settings_store import SettingsStore
from loginvrcast.device.adb_monitor import AdbMonitor
from loginvrcast.casting.scrcpy_manager import ScrcpyManager
from loginvrcast.ui.main_window import MainWindow

def resource_base_dir() -> Path:
    # PyInstaller onefile/onedir
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS"))
    # dev mode: walk up until we find /resources/app
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "resources" / "app").exists():
            return parent
    return here.parent

def main() -> int:
    app = QApplication(sys.argv)
    icon_path = resource_base_dir() / "resources" / "app" / "icon.png"
    app.setWindowIcon(QIcon(str(icon_path)))
    settings = SettingsStore.load()
    monitor = AdbMonitor(settings_store=settings)
    scrcpy = ScrcpyManager(settings_store=settings)

    win = MainWindow(settings_store=settings, adb_monitor=monitor, scrcpy_manager=scrcpy)
    win.show()

    monitor.start()  # 3s polling
    return app.exec()

if __name__ == "__main__":
    raise SystemExit(main())