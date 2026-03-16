from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from loginvrcast.core.state import AdbStatus
from loginvrcast.tools.subprocess_utils import run_quiet


def _is_windows() -> bool:
    return sys.platform.startswith("win")


def adb_filename() -> str:
    return "adb.exe" if _is_windows() else "adb"


def _candidate_platform_tools_dirs(selected_path: Path) -> list[Path]:
    """
    Expand a user-provided path into likely platform-tools directories.

    Supports selecting:
    - the platform-tools folder directly
    - Android SDK root folder (containing platform-tools/)
    - adb executable itself
    """
    p = selected_path.expanduser()

    candidates: list[Path] = []
    if p.is_file() and p.name == adb_filename():
        candidates.append(p.parent)

    candidates.append(p)
    candidates.append(p / "platform-tools")

    deduped: list[Path] = []
    seen: set[Path] = set()
    for c in candidates:
        if c in seen:
            continue
        seen.add(c)
        deduped.append(c)
    return deduped


def resolve_platform_tools_dir(selected_path: Path) -> tuple[Path | None, str]:
    """
    Resolve the best platform-tools directory from user-provided path.
    """
    first_error = "Folder does not exist."
    for candidate in _candidate_platform_tools_dirs(selected_path):
        ok, msg = validate_platform_tools_dir(candidate)
        if ok:
            return candidate, "OK"
        first_error = msg
    return None, first_error


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
        from loginvrcast.tools.subprocess_utils import run_quiet
        run_quiet([str(adb_path), "version"], timeout=2)
    except Exception:
        return False, "adb failed to run."

    return True, "OK"


def find_adb(platform_tools_dir: str | None, app_dir: Path) -> AdbStatus:
    # 1) user-chosen platform-tools folder
    if platform_tools_dir:
        resolved, _ = resolve_platform_tools_dir(Path(platform_tools_dir))
        if resolved:
            return AdbStatus(True, "ADB OK (custom folder)", str(resolved / adb_filename()))
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
            run_quiet([which, "version"], timeout=2)
            return AdbStatus(True, "ADB OK (PATH)", which)
        except Exception:
            pass
    return AdbStatus(False, "ADB not found. Provide platform-tools folder or add adb to PATH.", None)
