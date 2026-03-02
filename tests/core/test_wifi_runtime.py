from __future__ import annotations

from loginvrcast.core.state import DeviceInfo
from loginvrcast.core.wifi_runtime import build_wifi_plan


def test_plan_disabled_feature_returns_no_actions():
    plan = build_wifi_plan(
        wifi_enabled=False,
        connection_mode="usb_wifi",
        endpoint="192.168.1.2:5555",
        devices=[],
        now_s=100.0,
        last_tcpip_attempt_s=0.0,
        last_connect_attempt_s=0.0,
    )
    assert plan.status == ""
    assert plan.should_tcpip is False
    assert plan.should_connect is False


def test_plan_requires_endpoint_in_wifi_mode():
    plan = build_wifi_plan(
        wifi_enabled=True,
        connection_mode="usb_wifi",
        endpoint="",
        devices=[],
        now_s=100.0,
        last_tcpip_attempt_s=0.0,
        last_connect_attempt_s=0.0,
    )
    assert "set endpoint" in plan.status
    assert plan.target == ""


def test_plan_connected_network_device_short_circuits():
    plan = build_wifi_plan(
        wifi_enabled=True,
        connection_mode="usb_wifi",
        endpoint="192.168.1.2:5555",
        devices=[DeviceInfo(serial="192.168.1.2:5555", adb_state="device")],
        now_s=100.0,
        last_tcpip_attempt_s=0.0,
        last_connect_attempt_s=0.0,
    )
    assert "connected" in plan.status
    assert plan.should_tcpip is False
    assert plan.should_connect is False


def test_plan_triggers_tcpip_and_connect_when_due_and_usb_present():
    plan = build_wifi_plan(
        wifi_enabled=True,
        connection_mode="usb_wifi",
        endpoint="192.168.1.2:5555",
        devices=[DeviceInfo(serial="USB123", adb_state="device")],
        now_s=100.0,
        last_tcpip_attempt_s=0.0,
        last_connect_attempt_s=0.0,
    )
    assert plan.target == "192.168.1.2:5555"
    assert plan.should_tcpip is True
    assert plan.should_connect is True


def test_plan_respects_throttle_windows():
    plan = build_wifi_plan(
        wifi_enabled=True,
        connection_mode="usb_wifi",
        endpoint="192.168.1.2:5555",
        devices=[DeviceInfo(serial="USB123", adb_state="device")],
        now_s=10.0,
        last_tcpip_attempt_s=5.0,
        last_connect_attempt_s=6.0,
    )
    assert plan.should_tcpip is False
    assert plan.should_connect is False
