from __future__ import annotations


def wifi_controls_visible(*, wifi_enabled: bool, connection_mode: str) -> bool:
    return wifi_enabled and connection_mode == "usb_wifi"
