#!/usr/bin/env bash
set -euo pipefail

# Usage: ./scripts/build_usb_wifi.sh [extra pyinstaller args...]
export LOGINVRCAST_WIFI_ENABLED=1
pyinstaller "$@"
