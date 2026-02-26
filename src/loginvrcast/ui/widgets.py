from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QColor, QPainter
from PySide6.QtCore import QSize

from loginvrcast.core.state import Light


def app_dir_for_user_files() -> Path:
    """
    Folder next to the executable/.app that the user can drop platform-tools into.
    """
    if getattr(sys, "frozen", False):
        exe = Path(sys.executable).resolve()
        # macOS: .../LoginVRCast.app/Contents/MacOS/LoginVRCast
        if "Contents" in exe.parts and exe.parent.name == "MacOS":
            return exe.parents[3]  # folder containing the .app
        return exe.parent
    # dev mode: project root
    return Path(__file__).resolve().parents[3]


class TrafficLight(QWidget):
    def __init__(self):
        super().__init__()
        self._light = Light.RED

    def set_light(self, light: Light) -> None:
        self._light = light
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(24, 24)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        color = QColor("#d32f2f")  # red
        if self._light == Light.YELLOW:
            color = QColor("#fbc02d")
        elif self._light == Light.GREEN:
            color = QColor("#388e3c")

        painter.setBrush(color)
        painter.setPen(color)
        r = min(self.width(), self.height()) - 2
        painter.drawEllipse(1, 1, r, r)