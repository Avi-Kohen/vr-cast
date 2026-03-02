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

pyinstaller "${COMMON_ARGS[@]}" --runtime-hook scripts/pyi_runtime_wifi_off.py --name "LoginVRCast-USB" "$ENTRYPOINT"

pyinstaller "${COMMON_ARGS[@]}" --runtime-hook scripts/pyi_runtime_wifi_on.py --name "LoginVRCast-USB-WIFI" "$ENTRYPOINT"

echo "Built dist/LoginVRCast-USB.app and dist/LoginVRCast-USB-WIFI.app"
