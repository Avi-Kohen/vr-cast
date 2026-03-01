from __future__ import annotations

import subprocess
import sys
from typing import Sequence


def _windows_no_window_kwargs() -> dict:
    if not sys.platform.startswith("win"):
        return {}
    # More robust than CREATE_NO_WINDOW alone on some systems
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = subprocess.SW_HIDE
    return {
        "creationflags": subprocess.CREATE_NO_WINDOW,
        "startupinfo": si,
    }


def run_quiet(args: Sequence[str], *, timeout: float = 2.0) -> subprocess.CompletedProcess:
    kwargs = _windows_no_window_kwargs()
    return subprocess.run(list(args), check=True, timeout=timeout, capture_output=True, text=True, **kwargs)