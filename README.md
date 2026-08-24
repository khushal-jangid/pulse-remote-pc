# 📱 PulseRemote PC

> 🖥️ Control your PC directly from your smartphone browser — Mouse, Keyboard, Media, Screen, Webcam & System Controls.

**PulseRemote PC** is an advanced remote-control system that allows you to control and monitor a Windows PC from a smartphone browser over the same Wi-Fi network.

Instead of installing a traditional remote-control application on your phone, PulseRemote creates a local web-based control interface that can be opened directly from your smartphone.

The desktop application automatically starts the local server, detects the PC's Wi-Fi IP address, generates a QR code for quick connection, and provides a live server status and activity dashboard.

---

## ✨ Features

### 📱 Smartphone PC Control

Control your computer directly from your phone browser.

- 🖱️ Mouse movement
- 👆 Left/right click
- 🖱️ Double click
- 📜 Vertical scrolling
- ↔️ Horizontal scrolling
- ⌨️ Keyboard typing
- ⌨️ Individual key presses
- ⚡ Keyboard shortcuts / hotkeys

---

### 🎵 Media Controls

Control media playback from your smartphone.

- ▶️ Play
- ⏸️ Pause
- ⏭️ Next
- ⏮️ Previous
- 🔊 Media-related system controls

---

### ⚙️ System Controls

Perform useful system-level operations remotely.

- 🔒 Lock PC
- 🚀 Launch applications
- 💡 Brightness control
- 🧹 RAM cleanup
- 🗑️ Temporary-file cleanup
- 📋 Clipboard control
- 🪟 Open-window management
- 🎯 Focus specific windows

---

### 📺 Live Screen Streaming

PulseRemote supports real-time screen streaming.

You can:

- 🖥️ Start screen streaming
- ⏹️ Stop screen streaming
- 📱 View the PC screen from your phone
- ⚡ Receive frames through WebSocket communication

---

### 📷 Webcam Streaming

The system also supports webcam streaming.

- 📷 Start webcam stream
- ⏹️ Stop webcam stream
- 📱 View webcam frames remotely

---

### 📊 System Monitoring

Get live information about the connected PC.

The server exposes information including:

- 🖥️ Hostname
- 💻 Operating system
- 🧠 CPU count
- 💾 Total memory
- 📈 Available/free memory
- 🌐 Local IP address
- 🔌 Server port
- 👥 Connected devices

The `/api/info` endpoint also generates a QR code containing the local connection URL.

---

### 🔗 QR Code Connection

Connecting your smartphone is simple.

The desktop application automatically:

1. Detects the PC's local Wi-Fi IP.
2. Starts the PulseRemote server.
3. Creates a connection URL.
4. Generates a QR code.
5. Displays the QR code in the desktop application.
6. Lets you scan the QR code using your smartphone.

📱 **No manual IP typing required.**

---

### 👥 Connected Device Monitoring

The WebSocket server keeps track of connected clients.

It can identify:

- 📱 Mobile phones
- 💻 Desktop browsers
- 🌐 Client IP addresses
- 🕐 Connection time
- 👥 Number of connected clients

---

### 🔒 Auto-Lock Protection

PulseRemote includes an optional automatic lock feature.

When enabled, the system can lock the PC workstation if the connected mobile device disconnects.

This can provide an additional layer of physical proximity protection.

---

### 📁 File Transfer

The server provides a file upload endpoint that can save uploaded files directly into the PC's Downloads directory.

This allows files to be transferred from the smartphone to the computer through the remote interface.

---

## 🖥️ Desktop Control Application

PulseRemote includes a Python/PyQt6 desktop application.

The desktop application provides:

- 📱 PulseRemote branding
- 🟢 Server status
- 🔴 Server stop/start control
- 🔗 QR code connection
- 🌐 Local IP address
- 🔌 Port information
- 📋 Copy URL button
- 📜 Live activity logs

The application automatically starts the Node.js server and displays connection information. It also creates a Windows Firewall rule for TCP port `3000` when running on Windows. 

---

## 🛠️ Tech Stack

| Technology | Purpose |
|---|---|
| 🐍 **Python** | Desktop application & system bridge |
| 🟢 **Node.js** | Remote-control server |
| 🚀 **Express.js** | HTTP server & APIs |
| ⚡ **WebSocket (ws)** | Real-time communication |
| 🪟 **PowerShell** | Windows system interaction |
| 🎨 **PyQt6** | Desktop GUI |
| 📱 **HTML/CSS/JavaScript** | Smartphone control interface |
| 🔗 **QR Code** | Quick device connection |
| 🌐 **HTTP** | Local network communication |

The Node.js project uses Express, WebSocket, QRCode and CORS packages. 

---

## 🔄 How It Works

```text
                 📱 Smartphone
                       │
                       │ Same Wi-Fi
                       ▼
              ┌─────────────────┐
              │  Web Controller │
              │   HTML / JS UI  │
              └────────┬────────┘
                       │
                       │ WebSocket
                       ▼
              ┌─────────────────┐
              │  Node.js Server │
              │ Express + WS    │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │  PowerShell     │
              │     Bridge      │
              └────────┬────────┘
                       │
                       ▼
              🖥️ Windows PC
