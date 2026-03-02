#!/usr/bin/env bash
set -euo pipefail

# Usage: ./scripts/build_usb_only.sh [extra pyinstaller args...]
export LOGINVRCAST_WIFI_ENABLED=0
pyinstaller "$@"
