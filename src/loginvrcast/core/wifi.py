from __future__ import annotations

import re

_HOST_PATTERN = re.compile(r"^[a-zA-Z0-9.-]+$")
_IPV4_PATTERN = re.compile(r"\b((?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3})\b")


def parse_wifi_endpoint(raw: str) -> tuple[str, int]:
    cleaned = raw.strip()
    if not cleaned:
        return "", 5555

    if ":" not in cleaned:
        return cleaned, 5555

    host, _, port_s = cleaned.partition(":")
    try:
        port = int(port_s)
    except ValueError:
        port = 5555
    return host.strip(), port


def validate_wifi_endpoint(raw: str) -> tuple[bool, str]:
    host, port = parse_wifi_endpoint(raw)
    if not host:
        return False, "Wi-Fi endpoint is required. Use format: ip[:port]"

    if not _HOST_PATTERN.fullmatch(host):
        return False, "Host contains invalid characters. Use IP or hostname."

    if port < 1 or port > 65535:
        return False, "Port must be between 1 and 65535."

    return True, ""


def extract_ipv4(text: str) -> str | None:
    match = _IPV4_PATTERN.search(text)
    if not match:
        return None
    return match.group(1)
