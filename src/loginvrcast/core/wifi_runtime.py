from __future__ import annotations

from dataclasses import dataclass

from loginvrcast.core.state import DeviceInfo
from loginvrcast.core.wifi import parse_wifi_endpoint

TCPIP_INTERVAL_S = 30.0
CONNECT_INTERVAL_S = 8.0


@dataclass(frozen=True)
class WifiPlan:
    status: str
    target: str
    should_tcpip: bool
    should_connect: bool


def build_wifi_plan(
    *,
    wifi_enabled: bool,
    connection_mode: str,
    endpoint: str,
    devices: list[DeviceInfo],
    now_s: float,
    last_tcpip_attempt_s: float,
    last_connect_attempt_s: float,
) -> WifiPlan:
    if not wifi_enabled or connection_mode != "usb_wifi":
        return WifiPlan(status="", target="", should_tcpip=False, should_connect=False)

    host, port = parse_wifi_endpoint(endpoint)
    if not host:
        return WifiPlan(
            status="Wi-Fi: set endpoint (ip[:port])",
            target="",
            should_tcpip=False,
            should_connect=False,
        )

    target = f"{host}:{port}"
    if any(d.serial == target and d.adb_state == "device" for d in devices):
        return WifiPlan(
            status=f"Wi-Fi: connected to {target}",
            target=target,
            should_tcpip=False,
            should_connect=False,
        )

    usb_ready = any(d.adb_state == "device" and ":" not in d.serial for d in devices)
    should_tcpip = usb_ready and (now_s - last_tcpip_attempt_s) >= TCPIP_INTERVAL_S
    should_connect = (now_s - last_connect_attempt_s) >= CONNECT_INTERVAL_S

    return WifiPlan(
        status=f"Wi-Fi: trying {target}",
        target=target,
        should_tcpip=should_tcpip,
        should_connect=should_connect,
    )
