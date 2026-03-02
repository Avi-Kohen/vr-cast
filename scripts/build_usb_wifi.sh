#!/usr/bin/env bash
set -euo pipefail

# Usage: ./scripts/build_usb_wifi.sh [extra pyinstaller args...]
# Embeds a runtime hook so frozen app defaults to USB+Wi-Fi when env var is not set.
pyinstaller --runtime-hook scripts/pyi_runtime_wifi_on.py \
  --noconfirm --clean --onefile --windowed \
  --name LoginVRCast-USB-onefile \
  --paths src \
  --add-data "resources/scrcpy/win-x64:resources/scrcpy/win-x64" \
  --add-data "resources/app/icon.png:resources/app" \
  --icon resources/app/icon.ico \
  src/loginvrcast/app.py
