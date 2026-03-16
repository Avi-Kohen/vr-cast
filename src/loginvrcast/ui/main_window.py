from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QAction, QDesktopServices
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
from loginvrcast.tools.adb_locator import resolve_platform_tools_dir
from loginvrcast.core.wifi import validate_wifi_endpoint
from loginvrcast.core.ui_state import wifi_controls_visible
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

        self._build_menu_bar()

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
        self.wifi_status_label = QLabel("")
        self.wifi_status_label.setWordWrap(True)
        self.wifi_connect_btn = QPushButton("Connect Wi-Fi now")
        self.wifi_connect_btn.clicked.connect(self._on_connect_wifi_now)
        self.wifi_disconnect_btn = QPushButton("Disconnect Wi-Fi")
        self.wifi_disconnect_btn.clicked.connect(self._on_disconnect_wifi_now)

        wifi_action_row = QHBoxLayout()
        wifi_action_row.addWidget(self.wifi_connect_btn)
        wifi_action_row.addWidget(self.wifi_disconnect_btn)
        wifi_action_row.addStretch(1)
        wifi_action_widget = QWidget()
        wifi_action_widget.setLayout(wifi_action_row)

        adv_layout.addRow("Wi-Fi endpoint", self.wifi_endpoint_edit)
        adv_layout.addRow("", self.wifi_help_label)
        adv_layout.addRow("", wifi_action_widget)
        adv_layout.addRow("", self.wifi_status_label)

        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["Low", "Normal", "High"])
        self.quality_combo.setCurrentText(self.settings_store.settings.quality_preset)
        self.quality_combo.currentTextChanged.connect(self._on_settings_changed)
        adv_layout.addRow("Quality", self.quality_combo)

        self.crop_mode_combo = QComboBox()
        self.crop_mode_combo.addItem("Device Rendering (--crop)", "official")
        self.crop_mode_combo.addItem("Computer Rendering (--client-crop)", "client")
        idx = self.crop_mode_combo.findData(self.settings_store.settings.crop_mode)
        self.crop_mode_combo.setCurrentIndex(idx if idx != -1 else 0)
        self.crop_mode_combo.currentIndexChanged.connect(self._on_settings_changed)
        adv_layout.addRow("Rendering mode", self.crop_mode_combo)

        self.crop_combo = QComboBox()
        self.crop_combo.addItems([
            "1600:904:2017:510",
            "1600:900:2017:510",
            "1730:974:1934:450",
            "1450:1450:200:200",
        ])
        self.crop_combo.setCurrentText(self.settings_store.settings.crop_value)
        self.crop_combo.currentTextChanged.connect(self._on_settings_changed)
        adv_layout.addRow("Device Rendering", self.crop_combo)

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
        self.monitor.wifi_status_changed.connect(self._on_wifi_status_changed)
        self.scrcpy.started.connect(self._on_cast_started)
        self.scrcpy.stopped.connect(self._on_cast_stopped)
        self.scrcpy.error.connect(self._on_cast_error)

    def _build_menu_bar(self) -> None:
        menu = self.menuBar()

        file_menu = menu.addMenu("&File")
        exit_action = QAction("E&xit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        tools_menu = menu.addMenu("&Tools")

        browse_adb_action = QAction("Select platform-tools folder…", self)
        browse_adb_action.triggered.connect(self._browse_platform_tools)
        tools_menu.addAction(browse_adb_action)

        open_config_action = QAction("Open settings folder", self)
        open_config_action.triggered.connect(self._open_settings_folder)
        tools_menu.addAction(open_config_action)

        help_menu = menu.addMenu("&Help")

        setup_adb_action = QAction("ADB setup guide", self)
        setup_adb_action.triggered.connect(self._open_readme_setup)
        help_menu.addAction(setup_adb_action)

        about_action = QAction("About LoginVRCast", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _open_settings_folder(self) -> None:
        cfg_dir = self.settings_store.path.parent
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(cfg_dir)))

    def _open_readme_setup(self) -> None:
        QDesktopServices.openUrl(QUrl("https://github.com/Avi-Kohen/LoginVRCast#setup-adb"))

    def _show_about(self) -> None:
        QMessageBox.information(
            self,
            "About LoginVRCast",
            "LoginVRCast\nA simple GUI wrapper around scrcpy for Meta Quest casting.",
        )

    def _sync_wifi_controls(self) -> None:
        wifi_mode = wifi_controls_visible(
            wifi_enabled=self.wifi_enabled,
            connection_mode=self.connection_mode_combo.currentData() or "usb_only",
        )
        self.wifi_endpoint_edit.setVisible(wifi_mode)
        self.wifi_help_label.setVisible(wifi_mode)
        self.wifi_connect_btn.setVisible(wifi_mode)
        self.wifi_disconnect_btn.setVisible(wifi_mode)
        self.wifi_status_label.setVisible(wifi_mode)

    def _on_settings_changed(self, *_):
        s = self.settings_store.settings
        s.connection_mode = self.connection_mode_combo.currentData() or "usb_only"
        if not self.wifi_enabled:
            s.connection_mode = "usb_only"
            s.wifi_endpoint = ""
        else:
            s.wifi_endpoint = self.wifi_endpoint_edit.text().strip()
            if s.connection_mode == "usb_wifi" and s.wifi_endpoint:
                ok, msg = validate_wifi_endpoint(s.wifi_endpoint)
                if not ok:
                    self.wifi_status_label.setText(f"Wi-Fi: {msg}")
                else:
                    self.wifi_status_label.setText("")
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
        resolved, msg = resolve_platform_tools_dir(p)
        if not resolved:
            QMessageBox.critical(self, "Invalid platform-tools folder", msg)
            return

        self.settings_store.settings.platform_tools_dir = str(resolved)
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


    def _on_wifi_status_changed(self, msg: str):
        if self.connection_mode_combo.currentData() == "usb_wifi" and self.wifi_enabled:
            self.wifi_status_label.setText(msg)

    def _on_connect_wifi_now(self):
        if not self.wifi_enabled:
            return
        self._on_settings_changed()
        self.monitor.connect_wifi_now()

    def _on_disconnect_wifi_now(self):
        if not self.wifi_enabled:
            return
        self._on_settings_changed()
        self.monitor.disconnect_wifi_now()

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
        selected = self.monitor.selected_serial()

        self.device_combo.blockSignals(True)
        self.device_combo.clear()
        selected_index = -1
        for i, d in enumerate(self._devices):
            name = d.model or "Unknown"
            self.device_combo.addItem(f"{name} — {d.serial} — {d.adb_state}")
            if selected and d.serial == selected:
                selected_index = i
        if selected_index == -1 and self._devices:
            selected_index = 0
        self.device_combo.setCurrentIndex(selected_index)
        self.device_combo.blockSignals(False)

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
