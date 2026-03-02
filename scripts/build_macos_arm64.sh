#!/usr/bin/env bash
set -euo pipefail

# Build both macOS Apple Silicon app variants:
# - LoginVRCast-USB.app
# - LoginVRCast-USB-WIFI.app
#
# Usage:
#   ./scripts/build_macos_arm64.sh

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This script is intended for macOS." >&2
  exit 1
fi

if [[ "$(uname -m)" != "arm64" ]]; then
  echo "Warning: expected Apple Silicon (arm64), detected $(uname -m)." >&2
fi

ENTRYPOINT="src/loginvrcast/__main__.py"
COMMON_ARGS=(
  --noconfirm
  --clean
  --windowed
  --paths src
  --add-data "resources:resources"
)

export LOGINVRCAST_WIFI_ENABLED=0
pyinstaller "${COMMON_ARGS[@]}" --name "LoginVRCast-USB" "$ENTRYPOINT"

export LOGINVRCAST_WIFI_ENABLED=1
pyinstaller "${COMMON_ARGS[@]}" --name "LoginVRCast-USB-WIFI" "$ENTRYPOINT"

echo "Built dist/LoginVRCast-USB.app and dist/LoginVRCast-USB-WIFI.app"
