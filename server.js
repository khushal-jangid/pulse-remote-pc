const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const path = require('path');
const os = require('os');
const fs = require('fs');
const qrcode = require('qrcode');
const psBridge = require('./ps-bridge');

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

const PORT = process.env.PORT || 3000;
let autoLockOnDisconnect = false;

app.use(express.static(path.join(__dirname, 'public')));
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

const downloadsDir = path.join(os.homedir(), 'Downloads');

function getLocalIP() {
  const interfaces = os.networkInterfaces();
  let preferredIP = null;
  let fallbackIP = null;

  for (const name of Object.keys(interfaces)) {
    const isVirtual = /virtual|vbox|vmnet|vethernet|wsl|bluetooth|docker|hyper-v/i.test(name);
    for (const net of interfaces[name]) {
      if (net.family === 'IPv4' && !net.internal) {
        if (!isVirtual && !preferredIP) {
          preferredIP = net.address;
        } else if (!fallbackIP) {
          fallbackIP = net.address;
        }
      }
    }
  }
  return preferredIP || fallbackIP || '127.0.0.1';
}

const localIP = getLocalIP();
const serverURL = `http://${localIP}:${PORT}`;

let connectedClients = new Map();

// API routes
app.get('/api/info', async (req, res) => {
  let qrCodeData = '';
  try {
    qrCodeData = await qrcode.toDataURL(serverURL);
  } catch (err) {
    console.error('QR code generation error:', err);
  }

  res.json({
    url: serverURL,
    localIP,
    port: PORT,
    hostname: os.hostname(),
    platform: os.platform(),
    arch: os.arch(),
    totalMem: Math.round(os.totalmem() / (1024 * 1024 * 1024) * 10) / 10,
    freeMem: Math.round(os.freemem() / (1024 * 1024 * 1024) * 10) / 10,
    cpus: os.cpus().length,
    qrCode: qrCodeData,
    connectedCount: connectedClients.size
  });
});

// File Upload Endpoint
app.post('/api/upload', (req, res) => {
  try {
    const { fileName, fileData } = req.body;
    if (!fileName || !fileData) {
      return res.status(400).json({ error: 'Missing file data' });
    }

    const base64Data = fileData.replace(/^data:.*;base64,/, '');
    const buffer = Buffer.from(base64Data, 'base64');
    
    const targetPath = path.join(downloadsDir, fileName);
    fs.writeFileSync(targetPath, buffer);

    console.log(`\x1b[32m[File Uploaded]\x1b[0m Saved '${fileName}' to ${targetPath}`);
    res.json({ success: true, message: `File saved to PC Downloads: ${fileName}`, path: targetPath });
  } catch (err) {
    console.error('File Upload Error:', err);
    res.status(500).json({ error: err.message });
  }
});

// Direct PNG image of QR Code
app.get('/qr', async (req, res) => {
  res.setHeader('Content-Type', 'image/png');
  try {
    await qrcode.toFileStream(res, serverURL, {
      width: 400,
      margin: 2,
      color: { dark: '#000000', light: '#FFFFFF' }
    });
  } catch (err) {
    res.status(500).send('Error generating QR Code');
  }
});

// WebSocket Connection handling
wss.on('connection', (ws, req) => {
  const clientId = Math.random().toString(36).substring(2, 9);
  const userAgent = req.headers['user-agent'] || 'Unknown Device';
  const isMobile = /mobile|iphone|android|ipad/i.test(userAgent);
  
  const clientInfo = {
    id: clientId,
    device: isMobile ? 'Mobile Phone' : 'Desktop Browser',
    ip: req.socket.remoteAddress,
    connectedAt: new Date()
  };

  connectedClients.set(clientId, { ws, info: clientInfo });
  console.log(`\x1b[36m[Client Connected]\x1b[0m ${clientInfo.device} (${clientId}) from ${req.socket.remoteAddress}`);
  
  psBridge.send({ action: 'start_stats_stream' });
  broadcastClientList();

  // Handle incoming messages
  ws.on('message', (message) => {
    try {
      const data = JSON.parse(message);
      
      switch (data.type) {
        case 'ping':
          ws.send(JSON.stringify({ type: 'pong', timestamp: data.timestamp }));
          break;
        case 'get_open_windows':
          psBridge.send({ action: 'get_open_windows' });
          break;
        case 'focus_window':
          psBridge.send({ action: 'focus_window', app: data.app });
          break;
        case 'set_brightness':
          psBridge.send({ action: 'set_brightness', value: data.value });
          break;
        case 'trim_ram':
          psBridge.send({ action: 'trim_ram' });
          break;
        case 'clean_temp':
          psBridge.send({ action: 'clean_temp' });
          break;
        case 'start_motion_guard':
          psBridge.send({ action: 'start_motion_guard' });
          break;
        case 'stop_motion_guard':
          psBridge.send({ action: 'stop_motion_guard' });
          break;
        case 'set_auto_lock':
          autoLockOnDisconnect = !!data.enabled;
          break;
        case 'start_screen_stream':
          psBridge.send({ action: 'start_screen_stream' });
          break;
        case 'stop_screen_stream':
          psBridge.send({ action: 'stop_screen_stream' });
          break;
        case 'start_webcam_stream':
          psBridge.send({ action: 'start_webcam_stream' });
          break;
        case 'stop_webcam_stream':
          psBridge.send({ action: 'stop_webcam_stream' });
          break;
        case 'get_stats':
          psBridge.send({ action: 'get_stats' });
          break;
        case 'set_clipboard':
          psBridge.send({ action: 'set_clipboard', text: data.text });
          break;
        case 'move_rel':
          psBridge.send({ action: 'move_rel', dx: data.dx, dy: data.dy });
          break;
        case 'move_abs':
          psBridge.send({ action: 'move_abs', x: data.x, y: data.y });
          break;
        case 'click':
          psBridge.send({ action: 'click', button: data.button || 'left' });
          break;
        case 'double_click':
          psBridge.send({ action: 'double_click' });
          break;
        case 'mouse_down':
          psBridge.send({ action: 'mouse_down', button: data.button || 'left' });
          break;
        case 'mouse_up':
          psBridge.send({ action: 'mouse_up', button: data.button || 'left' });
          break;
        case 'scroll':
          psBridge.send({ action: 'scroll', dy: data.dy });
          break;
        case 'hscroll':
          psBridge.send({ action: 'hscroll', dx: data.dx });
          break;
        case 'type':
          psBridge.send({ action: 'type', text: data.text });
          break;
        case 'key':
          psBridge.send({ action: 'key', key: data.key });
          break;
        case 'hotkey':
          psBridge.send({ action: 'hotkey', combo: data.combo });
          break;
        case 'media':
          psBridge.send({ action: 'media', type: data.subType });
          break;
        case 'system':
          psBridge.send({ action: 'system', type: data.subType });
          break;
        case 'launch':
          psBridge.send({ action: 'launch', app: data.app });
          break;
        case 'request_screenshot':
          psBridge.send({ action: 'screenshot' });
          break;
      }
    } catch (e) {
      console.error('Error parsing WS message:', e);
    }
  });

  ws.on('close', () => {
    connectedClients.delete(clientId);
    console.log(`\x1b[33m[Client Disconnected]\x1b[0m Client ${clientId}`);
    
    if (isMobile && autoLockOnDisconnect) {
      console.log('\x1b[31m[Auto-Lock]\x1b[0m Mobile disconnected from Wi-Fi! Locking PC Workstation...');
      psBridge.send({ action: 'system', type: 'lock' });
    }

    if (connectedClients.size === 0) {
      psBridge.send({ action: 'stop_webcam_stream' });
      psBridge.send({ action: 'stop_screen_stream' });
      psBridge.send({ action: 'stop_stats_stream' });
      psBridge.send({ action: 'stop_motion_guard' });
    }

    broadcastClientList();
  });
});

function broadcastClientList() {
  const clientsList = Array.from(connectedClients.values()).map(c => c.info);
  const payload = JSON.stringify({
    type: 'clients_update',
    clients: clientsList
  });
  
  for (const { ws } of connectedClients.values()) {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(payload);
    }
  }
}

// Forward events
psBridge.on('screen_frame', (data) => {
  const payload = JSON.stringify(data);
  for (const { ws } of connectedClients.values()) {
    if (ws.readyState === WebSocket.OPEN) ws.send(payload);
  }
});

psBridge.on('webcam_frame', (data) => {
  const payload = JSON.stringify(data);
  for (const { ws } of connectedClients.values()) {
    if (ws.readyState === WebSocket.OPEN) ws.send(payload);
  }
});

psBridge.on('sys_stats', (data) => {
  const payload = JSON.stringify(data);
  for (const { ws } of connectedClients.values()) {
    if (ws.readyState === WebSocket.OPEN) ws.send(payload);
  }
});

psBridge.on('open_windows', (data) => {
  const payload = JSON.stringify(data);
  for (const { ws } of connectedClients.values()) {
    if (ws.readyState === WebSocket.OPEN) ws.send(payload);
  }
});

psBridge.on('intruder_alert', (data) => {
  const payload = JSON.stringify(data);
  for (const { ws } of connectedClients.values()) {
    if (ws.readyState === WebSocket.OPEN) ws.send(payload);
  }
});

psBridge.on('sys_alert', (data) => {
  const payload = JSON.stringify(data);
  for (const { ws } of connectedClients.values()) {
    if (ws.readyState === WebSocket.OPEN) ws.send(payload);
  }
});

// Start Server
server.listen(PORT, '0.0.0.0', async () => {
  console.log('\n=============================================================');
  console.log('   \x1b[1m\x1b[35mPULSEREMOTE PC - Advanced PC Remote Control Hub\x1b[0m');
  console.log('=============================================================');
  console.log(`  \x1b[32m✔ PC Server running on:\x1b[0m ${serverURL}`);
  console.log(`  \x1b[32m✔ Local PC Dashboard:\x1b[0m http://localhost:${PORT}`);
  console.log('-------------------------------------------------------------');
  console.log('  📱 \x1b[1mScan this QR Code from your Mobile Phone:\x1b[0m\n');
  
  try {
    const qrTerminal = await qrcode.toString(serverURL, { type: 'terminal', small: true });
    console.log(qrTerminal);
  } catch (err) {
    console.log(`Open in phone browser: ${serverURL}`);
  }
  
  console.log('-------------------------------------------------------------');
  console.log('  Press Ctrl+C to stop server.\n');
});
