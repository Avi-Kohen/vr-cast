from __future__ import annotations

from loginvrcast.core.features import wifi_feature_enabled


def test_wifi_feature_enabled_defaults_on(monkeypatch):
    monkeypatch.delenv("LOGINVRCAST_WIFI_ENABLED", raising=False)
    assert wifi_feature_enabled() is True


def test_wifi_feature_enabled_false_values(monkeypatch):
    for value in ("0", "false", "False", "off", "NO"):
        monkeypatch.setenv("LOGINVRCAST_WIFI_ENABLED", value)
        assert wifi_feature_enabled() is False


def test_wifi_feature_enabled_true_values(monkeypatch):
    for value in ("1", "true", "yes", "on", "anything"):
        monkeypatch.setenv("LOGINVRCAST_WIFI_ENABLED", value)
        assert wifi_feature_enabled() is True
