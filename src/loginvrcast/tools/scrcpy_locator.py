from __future__ import annotations

from pathlib import Path
import sys


def _resource_base_dir() -> Path:
    # PyInstaller support
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    # dev mode: repo root is two levels up from this file: src/loginvrcast/tools/...
    return Path(__file__).resolve().parents[3]


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