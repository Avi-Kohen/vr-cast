from __future__ import annotations

from loginvrcast.core.ui_state import wifi_controls_visible


def test_wifi_controls_visible_only_for_wifi_mode_and_enabled():
    assert wifi_controls_visible(wifi_enabled=True, connection_mode="usb_wifi") is True
    assert wifi_controls_visible(wifi_enabled=True, connection_mode="usb_only") is False
    assert wifi_controls_visible(wifi_enabled=False, connection_mode="usb_wifi") is False
