# LoginVRCast (USB + optional Wi-Fi)

A simple GUI wrapper around scrcpy for casting a Meta Quest headset.

## Features
- Windows + macOS (Apple Silicon)
- USB casting
- Optional USB + Wi-Fi workflow (`adb tcpip` + `adb connect`)
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
- **USB + Wi-Fi**: app can run `adb tcpip` (when USB device is present) and periodically run `adb connect <ip:port>`.

When using USB + Wi-Fi, set **Wi-Fi endpoint** (example: `192.168.1.50:5555`).

## Build two distributions from one project
You can create two dist variants from the same codebase:

### 1) USB-only dist
Disable Wi-Fi feature at runtime/build time:

```bash
LOGINVRCAST_WIFI_ENABLED=0 pyinstaller ...
```

Result:
- UI only shows USB mode
- Settings are forced to USB only
- App does not run `adb tcpip` or `adb connect`

### 2) USB + Wi-Fi dist
Use default (or explicitly enable):

```bash
LOGINVRCAST_WIFI_ENABLED=1 pyinstaller ...
```

Result:
- UI shows both modes
- Wi-Fi endpoint field is available
- App can prepare and connect over Wi-Fi

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

## Troubleshooting
- Red “ADB not found”: set platform-tools folder in Advanced
- Yellow “Unauthorized”: approve USB debugging prompt in headset
- No device in USB + Wi-Fi mode: connect USB once and verify Wi-Fi endpoint
