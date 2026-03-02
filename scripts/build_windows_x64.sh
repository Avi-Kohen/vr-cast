#!/usr/bin/env bash
set -euo pipefail

# Wrapper to invoke PowerShell Windows build script from Git Bash.
# Builds all variants by default: USB/USB-WIFI x onefile/onedir.

pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/build_windows_x64.ps1 "$@" || \
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build_windows_x64.ps1 "$@"
