from __future__ import annotations

import subprocess
import sys
from typing import Sequence


def run_quiet(args: Sequence[str], *, timeout: float = 2.0) -> subprocess.CompletedProcess:
    """
    Run a subprocess without flashing a console window on Windows.
    Captures stdout/stderr as text.
    """
    kwargs: dict = dict(
        capture_output=True,
        text=True,
        timeout=timeout,
        stdin=subprocess.DEVNULL,
    )

    if sys.platform.startswith("win"):
        # Primary: don't create a console window.
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

        # Extra safety: hide any window if created by the child process.
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
        kwargs["startupinfo"] = si

    return subprocess.run(list(args), **kwargs)