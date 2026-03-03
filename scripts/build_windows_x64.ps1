param(
  [switch]$OneFile,
  [switch]$OneDir,
  [switch]$UsbOnly,
  [switch]$UsbWifi,
  [string]$NamePrefix = "LoginVRCast",
  [string]$Entrypoint = "src/loginvrcast/app.py"
)

$ErrorActionPreference = "Stop"

if (-not $OneFile -and -not $OneDir) {
  $OneFile = $true
  $OneDir = $true
}
if (-not $UsbOnly -and -not $UsbWifi) {
  $UsbOnly = $true
  $UsbWifi = $true
}

$common = @(
  "--noconfirm",
  "--clean",
  "--windowed",
  "--paths", "src",
  "--add-data", "resources/scrcpy/win-x64;resources/scrcpy/win-x64",
  "--add-data", "resources/app/icon.png;resources/app",
  "--icon", "resources/app/icon.ico"
)

function Build-Variant([string]$name, [string]$hook, [string]$mode) {
  $pyinstallerArgs = @()
  $pyinstallerArgs += $common
  $pyinstallerArgs += "--runtime-hook"
  $pyinstallerArgs += $hook

  if ($mode -eq "onefile") {
    $pyinstallerArgs += "--onefile"
  }
  elseif ($mode -eq "onedir") {
    $pyinstallerArgs += "--onedir"
  }
  else {
    throw "Unsupported mode: $mode"
  }

  $pyinstallerArgs += "--name"
  $pyinstallerArgs += $name
  $pyinstallerArgs += $Entrypoint

  Write-Host "Building $name ($mode) ..."
  & pyinstaller @pyinstallerArgs
}

if ($UsbOnly) {
  if ($OneDir)  { Build-Variant "$NamePrefix-USB-onedir" "scripts/pyi_runtime_wifi_off.py" "onedir" }
  if ($OneFile) { Build-Variant "$NamePrefix-USB-onefile" "scripts/pyi_runtime_wifi_off.py" "onefile" }
}

if ($UsbWifi) {
  if ($OneDir)  { Build-Variant "$NamePrefix-USB-WIFI-onedir" "scripts/pyi_runtime_wifi_on.py" "onedir" }
  if ($OneFile) { Build-Variant "$NamePrefix-USB-WIFI-onefile" "scripts/pyi_runtime_wifi_on.py" "onefile" }
}