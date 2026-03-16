from __future__ import annotations

from pathlib import Path

import loginvrcast.tools.adb_locator as adb_locator


def _create_fake_adb(dir_path: Path) -> Path:
    adb_path = dir_path / adb_locator.adb_filename()
    adb_path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    adb_path.chmod(0o755)
    return adb_path


def test_resolve_platform_tools_dir_accepts_sdk_root(tmp_path, monkeypatch):
    sdk_root = tmp_path / "Android" / "Sdk"
    platform_tools = sdk_root / "platform-tools"
    platform_tools.mkdir(parents=True)
    _create_fake_adb(platform_tools)

    monkeypatch.setattr(adb_locator, "run_quiet", lambda *args, **kwargs: None)

    resolved, msg = adb_locator.resolve_platform_tools_dir(sdk_root)

    assert resolved == platform_tools
    assert msg == "OK"


def test_resolve_platform_tools_dir_accepts_adb_binary_path(tmp_path, monkeypatch):
    platform_tools = tmp_path / "platform-tools"
    platform_tools.mkdir(parents=True)
    adb_path = _create_fake_adb(platform_tools)

    monkeypatch.setattr(adb_locator, "run_quiet", lambda *args, **kwargs: None)

    resolved, msg = adb_locator.resolve_platform_tools_dir(adb_path)

    assert resolved == platform_tools
    assert msg == "OK"


def test_find_adb_uses_resolved_custom_folder(tmp_path, monkeypatch):
    sdk_root = tmp_path / "Library" / "Android" / "sdk"
    platform_tools = sdk_root / "platform-tools"
    platform_tools.mkdir(parents=True)
    adb_path = _create_fake_adb(platform_tools)

    monkeypatch.setattr(adb_locator, "run_quiet", lambda *args, **kwargs: None)

    status = adb_locator.find_adb(str(sdk_root), tmp_path)

    assert status.ok is True
    assert status.adb_path == str(adb_path)
    assert status.message == "ADB OK (custom folder)"
