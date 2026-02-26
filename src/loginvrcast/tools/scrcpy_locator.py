from __future__ import annotations

from pathlib import Path
import sys


def _resource_base_dir() -> Path:
    # PyInstaller
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)

    # Dev mode (editable install): walk up until we find resources/scrcpy
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "resources" / "scrcpy").exists():
            return parent

    # Fallback: typical src layout
    return here.parents[3]


def scrcpy_bundle_dir() -> Path:
    base = _resource_base_dir()
    return base / "resources" / "scrcpy"


def scrcpy_path_for_current_os() -> Path:
    bundle = scrcpy_bundle_dir()

    if sys.platform.startswith("win"):
        return bundle / "win-x64" / "scrcpy.exe"
    if sys.platform == "darwin":
        return bundle / "macos-arm64" / "scrcpy"
    raise RuntimeError("Unsupported OS in v1 (Windows + macOS only).")