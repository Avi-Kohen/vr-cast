from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from loginvrcast.casting.scrcpy_manager import ScrcpyManager
from loginvrcast.core.settings_store import SettingsStore
from loginvrcast.core.state import AdbStatus, DeviceInfo, Light
from loginvrcast.device.adb_monitor import AdbMonitor
from loginvrcast.tools.adb_locator import validate_platform_tools_dir
from loginvrcast.ui.widgets import TrafficLight


class MainWindow(QMainWindow):
    def __init__(
        self,
        settings_store: SettingsStore,
        adb_monitor: AdbMonitor,
        scrcpy_manager: ScrcpyManager,
        wifi_enabled: bool,
    ):
        super().__init__()
        self.setWindowTitle("LoginVRCast")

        self.settings_store = settings_store
        self.monitor = adb_monitor
        self.scrcpy = scrcpy_manager
        self.wifi_enabled = wifi_enabled

        self._adb_status: AdbStatus | None = None
        self._devices: list[DeviceInfo] = []

        root = QWidget()
        self.setCentralWidget(root)
        main = QVBoxLayout(root)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Device:"))
        self.device_combo = QComboBox()
        self.device_combo.currentIndexChanged.connect(self._on_device_selected)
        row1.addWidget(self.device_combo, 1)
        main.addLayout(row1)

        row2 = QHBoxLayout()
        self.light = TrafficLight()
        row2.addWidget(self.light)
        self.status_label = QLabel("Starting...")
        self.status_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        row2.addWidget(self.status_label, 1)
        main.addLayout(row2)

        self.details_label = QLabel("")
        self.details_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        main.addWidget(self.details_label)

        self.toggle_btn = QPushButton("Start Casting")
        self.toggle_btn.clicked.connect(self._on_toggle)
        self.toggle_btn.setEnabled(False)
        main.addWidget(self.toggle_btn)

        adv = QGroupBox("Advanced")
        adv.setCheckable(True)
        adv.setChecked(False)
        adv_layout = QFormLayout(adv)

        self.adb_label = QLabel("ADB: (auto)")
        self.browse_btn = QPushButton("Browse platform-tools folder…")
        self.browse_btn.clicked.connect(self._browse_platform_tools)
        adb_row = QHBoxLayout()
        adb_row.addWidget(self.adb_label, 1)
        adb_row.addWidget(self.browse_btn)
        adb_row_widget = QWidget()
        adb_row_widget.setLayout(adb_row)
        adv_layout.addRow("ADB", adb_row_widget)

        self.connection_mode_combo = QComboBox()
        self.connection_mode_combo.addItem("USB only", "usb_only")
        if self.wifi_enabled:
            self.connection_mode_combo.addItem("USB + Wi-Fi", "usb_wifi")
        else:
            self.settings_store.settings.connection_mode = "usb_only"
        idx = self.connection_mode_combo.findData(self.settings_store.settings.connection_mode)
        self.connection_mode_combo.setCurrentIndex(idx if idx != -1 else 0)
        self.connection_mode_combo.currentIndexChanged.connect(self._on_settings_changed)
        adv_layout.addRow("Connection mode", self.connection_mode_combo)

        self.wifi_endpoint_edit = QLineEdit(self.settings_store.settings.wifi_endpoint)
        self.wifi_endpoint_edit.setPlaceholderText("192.168.1.50:5555")
        self.wifi_endpoint_edit.editingFinished.connect(self._on_settings_changed)
        self.wifi_help_label = QLabel("Needs USB once to enable adb tcpip, then can reconnect by IP.")
        self.wifi_help_label.setWordWrap(True)
        adv_layout.addRow("Wi-Fi endpoint", self.wifi_endpoint_edit)
        adv_layout.addRow("", self.wifi_help_label)

        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["Low", "Normal", "High"])
        self.quality_combo.setCurrentText(self.settings_store.settings.quality_preset)
        self.quality_combo.currentTextChanged.connect(self._on_settings_changed)
        adv_layout.addRow("Quality", self.quality_combo)

        self.crop_mode_combo = QComboBox()
        self.crop_mode_combo.addItem("Official crop (--crop)", "official")
        self.crop_mode_combo.addItem("Client crop (--client-crop)", "client")
        idx = self.crop_mode_combo.findData(self.settings_store.settings.crop_mode)
        self.crop_mode_combo.setCurrentIndex(idx if idx != -1 else 0)
        self.crop_mode_combo.currentIndexChanged.connect(self._on_settings_changed)
        adv_layout.addRow("Crop mode", self.crop_mode_combo)

        self.crop_combo = QComboBox()
        self.crop_combo.addItems([
            "1600:904:2017:510",
            "1600:900:2017:510",
            "1730:974:1934:450",
            "1450:1450:200:200",
        ])
        self.crop_combo.setCurrentText(self.settings_store.settings.crop_value)
        self.crop_combo.currentTextChanged.connect(self._on_settings_changed)
        adv_layout.addRow("Crop", self.crop_combo)

        self.renderer_combo = QComboBox()
        self.renderer_combo.addItems(["direct3d", "opengl"])
        self.renderer_combo.setCurrentText(self.settings_store.settings.windows_renderer)
        self.renderer_combo.currentTextChanged.connect(self._on_settings_changed)
        if sys.platform.startswith("win"):
            adv_layout.addRow("Renderer (Windows)", self.renderer_combo)
        else:
            self.renderer_combo.setEnabled(False)

        main.addWidget(adv)

        self._sync_wifi_controls()

        self.monitor.adb_status_changed.connect(self._on_adb_status)
        self.monitor.devices_changed.connect(self._on_devices_changed)
        self.scrcpy.started.connect(self._on_cast_started)
        self.scrcpy.stopped.connect(self._on_cast_stopped)
        self.scrcpy.error.connect(self._on_cast_error)

    def _sync_wifi_controls(self) -> None:
        wifi_mode = self.connection_mode_combo.currentData() == "usb_wifi" and self.wifi_enabled
        self.wifi_endpoint_edit.setVisible(wifi_mode)
        self.wifi_help_label.setVisible(wifi_mode)

    def _on_settings_changed(self, *_):
        s = self.settings_store.settings
        s.connection_mode = self.connection_mode_combo.currentData() or "usb_only"
        if not self.wifi_enabled:
            s.connection_mode = "usb_only"
            s.wifi_endpoint = ""
        else:
            s.wifi_endpoint = self.wifi_endpoint_edit.text().strip()
        s.quality_preset = self.quality_combo.currentText()
        s.crop_mode = self.crop_mode_combo.currentData()
        s.crop_value = self.crop_combo.currentText()
        if sys.platform.startswith("win"):
            s.windows_renderer = self.renderer_combo.currentText()
        self.settings_store.save()
        self._sync_wifi_controls()
        self.monitor.refresh()

    def _browse_platform_tools(self):
        folder = QFileDialog.getExistingDirectory(self, "Select platform-tools folder")
        if not folder:
            return
        p = Path(folder)
        ok, msg = validate_platform_tools_dir(p)
        if not ok:
            QMessageBox.critical(self, "Invalid platform-tools folder", msg)
            return

        self.settings_store.settings.platform_tools_dir = str(p)
        self.settings_store.save()
        self.monitor.refresh()

    def _on_device_selected(self, idx: int):
        if idx < 0 or idx >= len(self._devices):
            self.monitor.set_selected_serial(None)
            return
        self.monitor.set_selected_serial(self._devices[idx].serial)

    def _on_toggle(self):
        if self.scrcpy.is_running():
            self.scrcpy.stop()
            return

        if not self._adb_status or not self._adb_status.ok or not self._adb_status.adb_path:
            return

        selected = self.monitor.selected_serial()
        if self._selected_light() != Light.GREEN:
            return

        self.scrcpy.start(adb_path=self._adb_status.adb_path, serial=selected)

    def _on_adb_status(self, status: AdbStatus):
        self._adb_status = status
        self.adb_label.setText(f"ADB: {status.message}" + (f" ({status.adb_path})" if status.adb_path else ""))
        self._render_state()

    def _on_devices_changed(self, devices: list):
        self._devices = list(devices)
        self._update_device_combo()
        self._render_state()

    def _on_cast_started(self):
        self.toggle_btn.setText("Stop Casting")
        self.toggle_btn.setEnabled(True)

    def _on_cast_stopped(self):
        self.toggle_btn.setText("Start Casting")
        self._render_state()

    def _on_cast_error(self, msg: str):
        QMessageBox.critical(self, "scrcpy error", msg)
        self.toggle_btn.setText("Start Casting")
        self._render_state()

    def _update_device_combo(self):
        self.device_combo.blockSignals(True)
        self.device_combo.clear()
        for d in self._devices:
            name = d.model or "Unknown"
            self.device_combo.addItem(f"{name} — {d.serial} — {d.adb_state}")
        self.device_combo.blockSignals(False)

        if self._devices:
            self.device_combo.setCurrentIndex(0)
        else:
            self.device_combo.setCurrentIndex(-1)

    def _selected_device(self) -> DeviceInfo | None:
        idx = self.device_combo.currentIndex()
        if idx < 0 or idx >= len(self._devices):
            return None
        return self._devices[idx]

    def _selected_light(self) -> Light:
        if not self._adb_status or not self._adb_status.ok:
            return Light.RED
        d = self._selected_device()
        if not d:
            return Light.RED
        if d.adb_state == "unauthorized":
            return Light.YELLOW
        if d.adb_state == "device":
            return Light.GREEN
        return Light.RED

    def _render_state(self):
        if self.scrcpy.is_running():
            self.light.set_light(self._selected_light())
            self.status_label.setText("Casting running…")
            d = self._selected_device()
            if d:
                self.details_label.setText(f"Model: {d.model or 'Unknown'}\nSerial: {d.serial}")
            return

        light = self._selected_light()
        self.light.set_light(light)

        if not self._adb_status or not self._adb_status.ok:
            self.status_label.setText("ADB not found. Provide platform-tools folder.")
            self.details_label.setText("")
            self.toggle_btn.setEnabled(False)
            self.toggle_btn.setText("Start Casting")
            return

        d = self._selected_device()
        if not d:
            mode = self.connection_mode_combo.currentData()
            if mode == "usb_wifi" and self.wifi_enabled:
                self.status_label.setText("No device connected. Connect USB once and set Wi-Fi endpoint.")
            else:
                self.status_label.setText("No device connected.")
            self.details_label.setText("")
            self.toggle_btn.setEnabled(False)
            self.toggle_btn.setText("Start Casting")
            return

        if light == Light.YELLOW:
            self.status_label.setText("Unauthorized. Put headset on and approve USB debugging.")
            self.details_label.setText(f"Serial: {d.serial}")
            self.toggle_btn.setEnabled(False)
            self.toggle_btn.setText("Start Casting")
            return

        if light == Light.GREEN:
            model = d.model or "Unknown"
            self.status_label.setText(f"Connected — {model} — {d.serial}")
            self.details_label.setText(f"Model: {model}\nSerial: {d.serial}")
            self.toggle_btn.setEnabled(True)
            self.toggle_btn.setText("Start Casting")
            return

        self.status_label.setText("Not ready.")
        self.details_label.setText(f"Serial: {d.serial}")
        self.toggle_btn.setEnabled(False)
        self.toggle_btn.setText("Start Casting")
