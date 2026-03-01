from __future__ import annotations

import subprocess
import sys
from typing import Sequence


def run_quiet(args: Sequence[str], *, timeout: float = 2.0) -> subprocess.CompletedProcess:
    """
    Run a subprocess without flashing a console window on Windows.
    """
    kwargs = dict(capture_output=True, text=True, timeout=timeout)

    if sys.platform.startswith("win"):
        # Prevent console window popups for console child processes.
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW  # Windows-only constant
    return subprocess.run(list(args), check=True, **kwargs)