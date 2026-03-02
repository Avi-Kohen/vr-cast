from __future__ import annotations

from loginvrcast.core.wifi import parse_wifi_endpoint


def test_parse_endpoint_empty_uses_default_port():
    assert parse_wifi_endpoint("") == ("", 5555)


def test_parse_endpoint_without_port_uses_default_port():
    assert parse_wifi_endpoint("192.168.1.10") == ("192.168.1.10", 5555)


def test_parse_endpoint_with_port():
    assert parse_wifi_endpoint("192.168.1.10:5566") == ("192.168.1.10", 5566)


def test_parse_endpoint_with_invalid_port_falls_back_to_default():
    assert parse_wifi_endpoint("192.168.1.10:bad") == ("192.168.1.10", 5555)
