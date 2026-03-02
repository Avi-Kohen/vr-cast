# LoginVRCast (USB + optional Wi-Fi)

A simple GUI wrapper around scrcpy for casting a Meta Quest headset.

## Features
- Windows + macOS (Apple Silicon)
- USB casting
- Optional USB + Wi-Fi workflow (`adb tcpip` + `adb connect`)
- Manual **Connect Wi-Fi now** / **Disconnect Wi-Fi** actions in Advanced
- Wi-Fi status line (connected / connect attempt / errors)
- Read-only casting (`--no-control`)
- PC audio off (`--no-audio`)
- Traffic-light headset status
- Presets: Low / Normal / High
- Crop modes:
  - Official crop (`--crop w:h:x:y`)
  - Client crop (`--client-crop=w:h:x:y`)
- Windows-only renderer toggle (`--render-driver`)

## Connection modes
In **Advanced → Connection mode**:
- **USB only**: classic behavior, no Wi-Fi connection attempts.
- **USB + Wi-Fi**: app prepares Wi-Fi connection details, but only attempts `adb tcpip` / `adb connect` after you click **Connect Wi-Fi now**.

When using USB + Wi-Fi, set **Wi-Fi endpoint** (example: `192.168.1.50:5555`).
If endpoint is empty, the app now tries to auto-detect headset Wi-Fi IP from a USB-connected device.

## Build two distributions from one project
You can create two dist variants from the same codebase:

### 1) USB-only dist
Disable Wi-Fi feature at runtime/build time:

```bash
./scripts/build_usb_only.sh <your-pyinstaller-args>
```

Result:
- UI only shows USB mode
- Settings are forced to USB only
- App does not run `adb tcpip` or `adb connect`
- Build embeds USB-only runtime default (Wi-Fi hidden even without env var)

### 2) USB + Wi-Fi dist
Use default (or explicitly enable):

```bash
./scripts/build_usb_wifi.sh <your-pyinstaller-args>
```

Result:
- UI shows both modes
- Wi-Fi endpoint field is available
- App can prepare and connect over Wi-Fi
- Wi-Fi status + manual connect tools are visible
- Build embeds Wi-Fi-enabled runtime default


### 3) Build both variants on macOS arm64
On Apple Silicon Mac, this script builds both `.app` bundles with resources included:

```bash
./scripts/build_macos_arm64.sh
```

Outputs:
- `dist/LoginVRCast-USB.app`
- `dist/LoginVRCast-USB-WIFI.app`

### 4) Build all Windows x64 variants (onefile + onedir)
From Windows (PowerShell or Git Bash), build all four outputs by default:

```bash
./scripts/build_windows_x64.sh
```

This creates:
- `LoginVRCast-USB-onedir`
- `LoginVRCast-USB-onefile`
- `LoginVRCast-USB-WIFI-onedir`
- `LoginVRCast-USB-WIFI-onefile`

Optional filters (PowerShell):
- `-UsbOnly` or `-UsbWifi`
- `-OneFile` or `-OneDir`

```powershell
./scripts/build_windows_x64.ps1 -UsbOnly -OneFile
```

## Requirements
### 1) Quest headset
- Enable Developer Mode + USB debugging
- Approve USB debugging prompt when connecting

### 2) ADB (platform-tools) – user supplied
This app does **not** ship platform-tools.

Options:
- Place `platform-tools/` folder next to the app
- Or choose it in Advanced → “Browse platform-tools folder…”

Windows platform-tools folder must contain:
- `adb.exe`
- `AdbWinApi.dll`
- `AdbWinUsbApi.dll`


## Verify it works

### USB-only run
```bash
LOGINVRCAST_WIFI_ENABLED=0 python -m loginvrcast
```
Checks:
- Advanced shows only **USB only** mode
- Casting works over USB
- No Wi-Fi endpoint UI

### USB + Wi-Fi run
```bash
LOGINVRCAST_WIFI_ENABLED=1 python -m loginvrcast
```
Checks:
- Advanced shows **USB only** and **USB + Wi-Fi**
- Wi-Fi endpoint input is visible in USB + Wi-Fi mode (or leave empty for auto-detect)
- Click **Connect Wi-Fi now** to run `adb tcpip`/`adb connect` once (manual only; no auto-connect loop)
- Click **Disconnect Wi-Fi** to disconnect the configured endpoint
- Wi-Fi status label shows recent operation results
- With endpoint set, device can appear as `<ip>:<port>` after `adb connect`

### Automated checks
```bash
pytest -q
python -m py_compile src/loginvrcast/**/*.py
```


## Releases (tags)
- Pushing a tag like `v1.2.3` triggers `.github/workflows/release.yml`.
- The workflow builds macOS arm64 USB-only and USB+Wi-Fi artifacts and publishes them to the GitHub Release.
- Optional signing/notarization is enabled when these repository secrets are configured:
  - `MACOS_CERT_B64`, `MACOS_CERT_PASSWORD`, `MACOS_SIGN_IDENTITY`
  - `APPLE_ID`, `APPLE_APP_PASSWORD`, `APPLE_TEAM_ID`

## CI
- GitHub Actions workflow runs unit tests and compile checks on push/PR (`.github/workflows/ci.yml`).
- CI also builds and uploads macOS arm64 zipped app artifacts for both USB-only and USB+Wi-Fi variants.

## Troubleshooting
- Red “ADB not found”: set platform-tools folder in Advanced
- Yellow “Unauthorized”: approve USB debugging prompt in headset
- No device in USB + Wi-Fi mode: connect USB once and verify Wi-Fi endpoint
