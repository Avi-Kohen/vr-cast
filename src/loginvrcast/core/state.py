from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Light(Enum):
    RED = "red"
    YELLOW = "yellow"
    GREEN = "green"


@dataclass(frozen=True)
class DeviceInfo:
    serial: str
    adb_state: str  # "device" | "unauthorized" | "offline" | ...
    model: str | None = None


@dataclass(frozen=True)
class AdbStatus:
    ok: bool
    message: str
    adb_path: str | None = None