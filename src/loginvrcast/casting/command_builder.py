from __future__ import annotations

import sys
from loginvrcast.core.settings_store import Settings

QUALITY_PRESETS = {
    "Low":    ["--max-fps", "30", "--max-size", "1024", "-b", "2M"],
    "Normal": ["--max-fps", "60", "--max-size", "1280", "-b", "6M"],
    "High":   ["--max-fps", "60", "--max-size", "1600", "-b", "12M"],
}

def _strip_max_size(args: list[str]) -> list[str]:
    out = []
    i = 0
    while i < len(args):
        if args[i] in ("--max-size", "-m"):
            i += 2  # skip flag + value
            continue
        out.append(args[i])
        i += 1
    return out

def build_scrcpy_args(settings: Settings) -> list[str]:
    args = ["--no-control", "--no-audio"]

    preset = QUALITY_PRESETS.get(settings.quality_preset, QUALITY_PRESETS["Low"])
    if settings.crop_mode == "client":
        preset = _strip_max_size(preset)  # <- key change
    args += preset

    if settings.crop_mode == "official":
        args += ["--crop", settings.crop_value]
    else:
        args += [f"--client-crop={settings.crop_value}"]

    if sys.platform.startswith("win") and settings.windows_renderer in ("opengl", "direct3d"):
        args += [f"--render-driver={settings.windows_renderer}"]

    return args