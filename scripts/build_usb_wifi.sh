#!/usr/bin/env bash
set -euo pipefail

# Usage: ./scripts/build_usb_wifi.sh [extra pyinstaller args...]
# Embeds a runtime hook so frozen app defaults to USB+Wi-Fi when env var is not set.
pyinstaller --runtime-hook scripts/pyi_runtime_wifi_on.py "$@"
