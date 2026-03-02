#!/usr/bin/env bash
set -euo pipefail

# Usage: ./scripts/build_usb_only.sh [extra pyinstaller args...]
# Embeds a runtime hook so frozen app defaults to USB-only even when env var is not set.
pyinstaller --runtime-hook scripts/pyi_runtime_wifi_off.py "$@"
