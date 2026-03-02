from __future__ import annotations

from loginvrcast.core.wifi import parse_wifi_endpoint, validate_wifi_endpoint


def test_parse_endpoint_empty_uses_default_port():
    assert parse_wifi_endpoint("") == ("", 5555)


def test_parse_endpoint_without_port_uses_default_port():
    assert parse_wifi_endpoint("192.168.1.10") == ("192.168.1.10", 5555)


def test_parse_endpoint_with_port():
    assert parse_wifi_endpoint("192.168.1.10:5566") == ("192.168.1.10", 5566)


def test_parse_endpoint_with_invalid_port_falls_back_to_default():
    assert parse_wifi_endpoint("192.168.1.10:bad") == ("192.168.1.10", 5555)


def test_validate_endpoint_missing_host():
    ok, msg = validate_wifi_endpoint("")
    assert ok is False
    assert "required" in msg


def test_validate_endpoint_invalid_host_chars():
    ok, msg = validate_wifi_endpoint("bad host:5555")
    assert ok is False
    assert "invalid characters" in msg


def test_validate_endpoint_out_of_range_port():
    ok, msg = validate_wifi_endpoint("192.168.1.10:70000")
    assert ok is False
    assert "between 1 and 65535" in msg


def test_validate_endpoint_valid_host_and_port():
    ok, msg = validate_wifi_endpoint("quest.local:5555")
    assert ok is True
    assert msg == ""
