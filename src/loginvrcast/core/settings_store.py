from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path

from platformdirs import user_config_dir


@dataclass
class Settings:
    schema_version: int = 1

    # ADB
    platform_tools_dir: str | None = None  # folder containing adb(.exe)

    # Defaults you locked
    quality_preset: str = "Low"            # Low/Normal/High
    crop_mode: str = "official"            # official/client
    crop_value: str = "1600:904:2017:510"  # default
    windows_renderer: str = "direct3d"     # opengl/direct3d

    # Connection
    connection_mode: str = "usb_only"     # usb_only / usb_wifi
    wifi_endpoint: str = ""               # ip[:port], used in usb_wifi mode


class SettingsStore:
    APP_NAME = "LoginVRCast"

    def __init__(self, settings: Settings, path: Path):
        self.settings = settings
        self.path = path

    @classmethod
    def config_path(cls) -> Path:
        base = Path(user_config_dir(appname=cls.APP_NAME))
        base.mkdir(parents=True, exist_ok=True)
        return base / "settings.json"

    @classmethod
    def load(cls) -> "SettingsStore":
        path = cls.config_path()
        if not path.exists():
            return cls(Settings(), path)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            s = Settings(**data)
            return cls(s, path)
        except Exception:
            # If corrupted, start fresh (keep simple for v1)
            return cls(Settings(), path)

    def save(self) -> None:
        self.path.write_text(json.dumps(asdict(self.settings), indent=2), encoding="utf-8")