param(
  [switch]$OneFile,
  [switch]$OneDir,
  [switch]$UsbOnly,
  [switch]$UsbWifi,
  [string]$NamePrefix = "LoginVRCast",
  [string]$Entrypoint = "src/loginvrcast/__main__.py"
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
  "--add-data", "resources;resources",
  "--icon", "resources/app/icon.ico"
)

function Build-Variant([string]$name, [string]$hook, [switch]$onefile) {
  $args = @()
  $args += $common
  $args += "--runtime-hook"
  $args += $hook
  if ($onefile) { $args += "--onefile" }
  $args += "--name"
  $args += $name
  $args += $Entrypoint

  Write-Host "Building $name ..."
  & pyinstaller @args
}

if ($UsbOnly) {
  if ($OneDir)  { Build-Variant "$NamePrefix-USB-onedir" "scripts/pyi_runtime_wifi_off.py" $false }
  if ($OneFile) { Build-Variant "$NamePrefix-USB-onefile" "scripts/pyi_runtime_wifi_off.py" $true }
}

if ($UsbWifi) {
  if ($OneDir)  { Build-Variant "$NamePrefix-USB-WIFI-onedir" "scripts/pyi_runtime_wifi_on.py" $false }
  if ($OneFile) { Build-Variant "$NamePrefix-USB-WIFI-onefile" "scripts/pyi_runtime_wifi_on.py" $true }
}
