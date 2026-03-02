from __future__ import annotations

import os


def wifi_feature_enabled() -> bool:
    """Build/runtime feature switch for Wi-Fi functionality.

    Set LOGINVRCAST_WIFI_ENABLED=0 to produce a USB-only distribution.
    """
    raw = os.getenv("LOGINVRCAST_WIFI_ENABLED", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}
