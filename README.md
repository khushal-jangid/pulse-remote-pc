# ⚡ Pulse Remote v2.0 — Local Wi-Fi PC Remote Hub

[![Release](https://img.shields.io/badge/Release-v2.0.0-blue.svg)](https://github.com/khushal-jangid/pulse-remote-pc/releases/latest)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D6.svg?logo=windows)](https://github.com/khushal-jangid/pulse-remote-pc)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Download EXE](https://img.shields.io/badge/Download-PulseRemote.exe-success.svg?logo=windows)](https://github.com/khushal-jangid/pulse-remote-pc/releases/latest/download/PulseRemote.exe)

A high-performance, private, zero-latency Windows PC remote control system over **Local Wi-Fi (LAN)**. Control your mouse, keyboard, media, active monitors, webcam, and system utilities directly from your smartphone's web browser without installing any app on your phone.

---

## 📥 Quick Download (No Python Needed!)

👉 **[Download PulseRemote.exe (Latest Release)](https://github.com/khushal-jangid/pulse-remote-pc/releases/latest/download/PulseRemote.exe)**

1. Download **`PulseRemote.exe`** on your Windows PC.
2. Double-click to run.
3. Scan the **terminal QR code** with your smartphone camera.
4. Paired instantly! No installation, no login, and zero internet data used.

---

## 🌟 Key Features

| Feature | Description |
|---|---|
| 📡 **Direct Local Wi-Fi** | Operates over LAN with <1ms response time and 100% privacy (zero cloud dependency). |
| 📱 **Instant QR Code Pairing** | High-contrast terminal QR code with white quiet-zone border for instant camera scanning. |
| 🖱️ **Precision Touchpad** | Smooth touch-to-drag surface with Left, Right, and Middle click buttons. |
| ⌨️ **Full Remote Keyboard** | Type text directly, press navigation keys, and trigger hotkeys remotely. |
| 🚨 **1-Tap Boss / Panic Key** | Instantly hides all active windows (`Win+D`) and mutes PC master audio. |
| ☀️ **Screen Brightness Slider** | Adjust display brightness (0-100%) with quick presets (25%, 50%, 75%, 100%). |
| 📈 **Live Hardware HUD** | 2-second real-time CPU %, RAM usage, C: drive disk space, and network telemetry. |
| 🔋 **Laptop Battery Alerts** | Real-time battery percentage gauge with low-battery (20%) and full-charge (100%) alerts. |
| 🛡️ **Stealth PC Guard (CCTV)** | Mouse movement triggers a stealth webcam snapshot and sends an instant intruder alert to your phone. |
| 🚶 **Proximity Auto-Lock** | Automatically locks your Windows workstation when your phone disconnects or leaves Wi-Fi range. |
| 🖥️ **Multi-Monitor Switcher** | Auto-detects all connected screens with 1-tap display switcher and coordinate mapping. |
| 📷 **Live Webcam Streaming** | Low-latency live video streaming directly from your PC webcam to your smartphone. |
| 🎵 **Advanced Media Hub** | Play, Pause, Next, Previous, Volume +, Volume -, and Mute controls. |
| 🚀 **Quick App Launchers** | 1-Tap launch for Chrome, VS Code, File Explorer, Notepad, Task Manager, Terminal, Calc, Settings. |
| 🔔 **Find My PC Alarm** | Triggers an audible alarm on your PC to help locate it quickly in your room or office. |
| 📁 **Universal File Transfers** | Bidirectional file uploads and downloads between phone and PC Downloads folder. |

---

## 🖥️ Terminal Hub & Hotkeys

Pulse Remote runs directly in the terminal as a unified hub with live hotkey controls:

```text
====================================================================
          ⚡ PULSE REMOTE v2.0 - LOCAL WI-FI PC AGENT
====================================================================
  🖥️  PC Name:       Victus (Windows 10)
  🌐 Server URL:    http://192.168.1.100:8000
  🔑 Pairing PIN:   456 738  (For manual entry)
  ⏱️  Token Expiry:  04:59
  📡 Monitors:      1 active display(s)
  ⚡ Status:        🟡 Ready for connection (Waiting for smartphone...)
====================================================================
  📱 SCAN THIS QR CODE WITH YOUR PHONE CAMERA TO CONNECT:

  [HIGH-CONTRAST TERMINAL QR CODE]

  🔗 Direct Pairing Link: http://192.168.1.100:8000/?pair=456738
  💡 Or open browser and enter PIN: 456 738
====================================================================
  HOTKEYS:  [R] New QR / PIN    [T] Toggle QR Size    [D] Disconnect All
            [O] Open in Browser [S] Stop Alarm        [Q] Quit Agent
====================================================================
```

### Terminal Shortcuts:
- <kbd>R</kbd> — Generate a new temporary pairing token & refresh QR code.
- <kbd>T</kbd> — Toggle terminal QR code size between *Compact* (half-block) and *Large* (double-space).
- <kbd>D</kbd> — Revoke active sessions and disconnect all paired phones.
- <kbd>O</kbd> — Open the controller directly in your default PC browser.
- <kbd>S</kbd> — Silence the "Find My PC" alarm if ringing.
- <kbd>Q</kbd> — Safely shutdown the PC agent server.

---

## 🛠️ Tech Stack & Architecture

```text
  📱 Smartphone Browser (iOS / Android)
             │
             │ Local Wi-Fi (HTTP & WebSocket)
             ▼
    ┌─────────────────┐
    │  aiohttp Server │ (Port 8000)
    └────────┬────────┘
             ├──▶ Mouse & Keyboard Controller (PyAutoGUI)
             ├──▶ Screen Capture Engine (MSS / PIL)
             ├──▶ Webcam Video Streamer (OpenCV)
             ├──▶ System Telemetry & Process Management (psutil)
             └──▶ Session & Cryptographic Token Engine
```

- **Backend / Core Agent:** Python 3.10+, `aiohttp`, `websockets`, `pyautogui`, `mss`, `opencv-python`, `pillow`, `psutil`, `qrcode`.
- **Frontend / Client Controller:** Modern HTML5, CSS3 Glassmorphism, Vanilla ES6 JavaScript (zero third-party web frameworks, lightning-fast execution).
- **Packaging:** Standalone Windows `.exe` created with PyInstaller.

---

## 🐍 Running from Source (Developer Setup)

If you prefer to run from Python source code:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/khushal-jangid/pulse-remote-pc.git
   cd pulse-remote-pc
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the PC Agent:**
   ```bash
   # Run directly in Terminal Hub (Recommended)
   python agent.py

   # Or run with desktop GUI window
   python agent.py --gui
   ```

4. **Build your own `.exe`:**
   Double-click `build_exe.bat` or run:
   ```bash
   python build_exe.py
   ```

---

## 📄 License

This project is open-source and available under the [MIT License](LICENSE).
