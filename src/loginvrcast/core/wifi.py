from __future__ import annotations


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
