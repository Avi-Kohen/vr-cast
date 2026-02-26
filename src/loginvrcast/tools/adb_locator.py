from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from loginvrcast.core.state import AdbStatus


def _is_windows() -> bool:
    return sys.platform.startswith("win")


def adb_filename() -> str:
    return "adb.exe" if _is_windows() else "adb"


def validate_platform_tools_dir(dir_path: Path) -> tuple[bool, str]:
    """
    Strict validation (as you requested):
    - Windows: must contain adb.exe + AdbWinApi.dll + AdbWinUsbApi.dll
    - macOS: must contain adb executable
    """
    if not dir_path.exists() or not dir_path.is_dir():
        return False, "Folder does not exist."

    adb_path = dir_path / adb_filename()
    if not adb_path.exists():
        return False, f"Missing {adb_filename()}."

    if _is_windows():
        if not (dir_path / "AdbWinApi.dll").exists():
            return False, "Missing AdbWinApi.dll."
        if not (dir_path / "AdbWinUsbApi.dll").exists():
            return False, "Missing AdbWinUsbApi.dll."
    else:
        if not os.access(adb_path, os.X_OK):
            return False, "adb is not executable (chmod +x)."

    # Validate it actually runs
    try:
        subprocess.run([str(adb_path), "version"], capture_output=True, text=True, timeout=2, check=True)
    except Exception:
        return False, "adb failed to run."

    return True, "OK"


def find_adb(platform_tools_dir: str | None, app_dir: Path) -> AdbStatus:
    # 1) user-chosen platform-tools folder
    if platform_tools_dir:
        p = Path(platform_tools_dir)
        ok, msg = validate_platform_tools_dir(p)
        if ok:
            return AdbStatus(True, "ADB OK (custom folder)", str(p / adb_filename()))
        # If invalid, fall through (keep simple)
    # 2) ./platform-tools next to app
    local = app_dir / "platform-tools"
    ok, msg = validate_platform_tools_dir(local)
    if ok:
        return AdbStatus(True, "ADB OK (local platform-tools)", str(local / adb_filename()))
    # 3) PATH
    which = shutil.which(adb_filename())
    if which:
        try:
            subprocess.run([which, "version"], capture_output=True, text=True, timeout=2, check=True)
            return AdbStatus(True, "ADB OK (PATH)", which)
        except Exception:
            pass
    return AdbStatus(False, "ADB not found. Provide platform-tools folder or add adb to PATH.", None)