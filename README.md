# LoginVRCast (USB-only)

A simple GUI wrapper around scrcpy for casting a Meta Quest headset over **USB**.

## Features (v1)
- Windows + macOS (Apple Silicon)
- **USB only** (no Wi-Fi)
- **Read-only** casting (`--no-control`)
- **PC audio always off** (`--no-audio`)
- Traffic-light headset status:
  - Red = not connected / ADB missing
  - Yellow = unauthorized
  - Green = ready
- Presets: Low / Normal / High
- Crop modes:
  - Official crop (`--crop w:h:x:y`)
  - Client crop (custom: `--client-crop=w:h:x:y`)
- Windows only: renderer toggle OpenGL / Direct3D (`--render-driver`)

## Requirements
### 1) Quest headset
- Enable Developer Mode + USB debugging
- Approve USB debugging prompt when connecting

### 2) ADB (platform-tools) – user supplied
This app does **not** ship platform-tools.
You have 2 options:
- **Offline**: place a `platform-tools/` folder next to the app
- **Online**: download platform-tools and select the folder in Advanced → “Browse platform-tools folder…”

Windows platform-tools folder must contain:
- adb.exe
- AdbWinApi.dll
- AdbWinUsbApi.dll

## Usage
1) Connect Quest via USB
2) Approve USB debugging inside the headset
3) Status turns Green → click **Start Casting**
4) Click **Stop Casting** to stop (monitor continues)

## Default settings
- Quality preset: Low
- Crop mode: Official
- Default crop: 1600:904:2017:510

## Troubleshooting
- Red “ADB not found”: set platform-tools folder in Advanced
- Yellow “Unauthorized”: approve USB debugging prompt in headset
- Client crop black screen: (fixed in v1) client crop ignores max-size to avoid out-of-bounds crop