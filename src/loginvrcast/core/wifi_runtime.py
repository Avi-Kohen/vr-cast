from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

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


@dataclass(frozen=True)
class WifiExecutionResult:
    status: str
    tcpip_attempt_s: float
    connect_attempt_s: float


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


def execute_wifi_plan(
    *,
    plan: WifiPlan,
    adb_path: str,
    endpoint: str,
    devices: list[DeviceInfo],
    now_s: float,
    last_tcpip_attempt_s: float,
    last_connect_attempt_s: float,
    run_cmd: Callable[[list[str]], str],
) -> WifiExecutionResult:
    status = plan.status
    tcpip_attempt_s = last_tcpip_attempt_s
    connect_attempt_s = last_connect_attempt_s

    if not plan.target:
        return WifiExecutionResult(status=status, tcpip_attempt_s=tcpip_attempt_s, connect_attempt_s=connect_attempt_s)

    if plan.should_tcpip:
        usb_ready = next((d for d in devices if d.adb_state == "device" and ":" not in d.serial), None)
        if usb_ready:
            tcpip_attempt_s = now_s
            try:
                _, port = parse_wifi_endpoint(endpoint)
                run_cmd([adb_path, "-s", usb_ready.serial, "tcpip", str(port)])
                status = f"Wi-Fi: enabled tcpip:{port} via USB"
            except Exception as e:
                status = f"Wi-Fi: tcpip failed ({e})"

    if plan.should_connect:
        connect_attempt_s = now_s
        try:
            out = run_cmd([adb_path, "connect", plan.target]).strip()
            status = f"Wi-Fi: {out or 'connect attempted'}"
        except Exception as e:
            status = f"Wi-Fi: connect failed ({e})"

    return WifiExecutionResult(status=status, tcpip_attempt_s=tcpip_attempt_s, connect_attempt_s=connect_attempt_s)


def apply_manual_connect_policy(*, manual_connect_requested: bool, plan_status: str, target: str) -> tuple[bool, str]:
    if not target:
        return False, plan_status

    if manual_connect_requested:
        return True, plan_status

    if "connected to" in plan_status:
        return False, plan_status

    return False, f"Wi-Fi: ready ({target}) — press Connect Wi-Fi now"
