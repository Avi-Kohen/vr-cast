from __future__ import annotations

import sys
from loginvrcast.core.settings_store import Settings

QUALITY_PRESETS: dict[str, list[str]] = {
    "Low":    ["--max-fps", "30", "--max-size", "1024", "-b", "2M"],
    "Normal": ["--max-fps", "60", "--max-size", "1280", "-b", "6M"],
    "High":   ["--max-fps", "60", "--max-size", "1600", "-b", "12M"],
}


def build_scrcpy_args(settings: Settings) -> list[str]:
    args: list[str] = []

    # locked v1
    args += ["--no-control", "--no-audio"]

    # quality
    args += QUALITY_PRESETS.get(settings.quality_preset, QUALITY_PRESETS["Low"])

    # crop
    if settings.crop_mode == "official":
        args += ["--crop", settings.crop_value]
    else:
        # your custom build uses --client-crop=<...>
        args += [f"--client-crop={settings.crop_value}"]

    # renderer (Windows only)
    if sys.platform.startswith("win"):
        if settings.windows_renderer in ("opengl", "direct3d"):
            args += [f"--render-driver={settings.windows_renderer}"]

    return args