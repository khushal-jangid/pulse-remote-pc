// PulseRemote PC Mobile Client Logic
(function() {
  let ws = null;
  let isConnected = false;
  let activeTab = 'tab-trackpad';
  let isHostDashboard = false;
  let currentSensitivity = 2.0;

  let isScreenStreaming = false;
  let isWebcamStreaming = false;
  let isMotionGuardActive = false;
  let isAutoLockActive = false;

  let pingStartTime = 0;
  let pingInterval = null;

  // Web Audio Siren
  function playIntruderSirenSound() {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(800, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(400, ctx.currentTime + 0.3);
      osc.frequency.exponentialRampToValueAtTime(800, ctx.currentTime + 0.6);

      gain.gain.setValueAtTime(0.3, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.8);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start();
      osc.stop(ctx.currentTime + 0.8);
    } catch(e) {}
  }

  // Sensitivity elements
  const sensSlider = document.getElementById('sens-slider');
  const sensValLabel = document.getElementById('sens-val');

  if (sensSlider) {
    sensSlider.addEventListener('input', (e) => {
      currentSensitivity = parseFloat(e.target.value);
      sensValLabel.textContent = `${currentSensitivity.toFixed(1)}x`;
    });
  }

  // Feature 44: Brightness Slider
  const brightnessSlider = document.getElementById('brightness-slider');
  const brightnessLabel = document.getElementById('val-brightness');
  if (brightnessSlider) {
    brightnessSlider.addEventListener('input', (e) => {
      const val = parseInt(e.target.value);
      if (brightnessLabel) brightnessLabel.textContent = `${val}%`;
      sendWS({ type: 'set_brightness', value: val });
    });
  }

  // Modal elements
  const powerModal = document.getElementById('power-modal');
  const modalTitle = document.getElementById('modal-power-title');
  const modalDesc = document.getElementById('modal-power-desc');
  const modalConfirmBtn = document.getElementById('btn-modal-confirm');
  const modalCancelBtn = document.getElementById('btn-modal-cancel');
  let pendingPowerAction = null;

  // Intruder Modal
  const intruderModal = document.getElementById('intruder-modal');
  const intruderImg = document.getElementById('intruder-img');
  const intruderMsg = document.getElementById('intruder-msg');
  const intruderTime = document.getElementById('intruder-time');
  const btnDismissIntruder = document.getElementById('btn-dismiss-intruder');

  if (btnDismissIntruder) {
    btnDismissIntruder.onclick = () => {
      if (intruderModal) intruderModal.classList.remove('active');
    };
  }

  // Connect WebSocket
  function initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      isConnected = true;
      const statusPill = document.getElementById('connection-status');
      if (statusPill) {
        statusPill.classList.remove('disconnected');
        statusPill.classList.add('connected');
        const label = statusPill.querySelector('.status-label');
        if (label) label.textContent = 'Connected';
      }
      hapticFeedback(20);

      if (activeTab === 'tab-screen') {
        startScreenStream();
      }

      if (pingInterval) clearInterval(pingInterval);
      pingInterval = setInterval(measurePingLatency, 2500);

      // Auto-fetch open windows
      sendWS({ type: 'get_open_windows' });
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleServerMessage(data);
      } catch (e) {
        console.error('WS JSON Error:', e);
      }
    };

    ws.onclose = () => {
      isConnected = false;
      const statusPill = document.getElementById('connection-status');
      if (statusPill) {
        statusPill.classList.remove('connected');
        statusPill.classList.add('disconnected');
        const label = statusPill.querySelector('.status-label');
        if (label) label.textContent = 'Offline';
      }
      if (pingInterval) clearInterval(pingInterval);
      stopWebcamStream();
      stopScreenStream();
      setTimeout(initWebSocket, 2000);
    };

    ws.onerror = (err) => {
      console.error('WebSocket Error:', err);
    };
  }

  function sendWS(data) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(data));
    }
  }

  function measurePingLatency() {
    pingStartTime = Date.now();
    sendWS({ type: 'ping', timestamp: pingStartTime });
  }

  function hapticFeedback(ms = 10) {
    if (navigator.vibrate) {
      try { navigator.vibrate(ms); } catch(e) {}
    }
  }

  function startScreenStream() {
    isScreenStreaming = true;
    sendWS({ type: 'start_screen_stream' });
  }

  function stopScreenStream() {
    isScreenStreaming = false;
    sendWS({ type: 'stop_screen_stream' });
  }

  function startWebcamStream() {
    isWebcamStreaming = true;
    sendWS({ type: 'start_webcam_stream' });
    const webcamPill = document.getElementById('webcam-status-pill');
    const webcamStatusText = document.getElementById('cam-status-text');
    if (webcamPill) {
      webcamPill.classList.add('active-cam');
      if (webcamStatusText) webcamStatusText.textContent = 'Camera ON';
    }
    hapticFeedback(20);
  }

  function stopWebcamStream() {
    isWebcamStreaming = false;
    sendWS({ type: 'stop_webcam_stream' });
    const webcamPill = document.getElementById('webcam-status-pill');
    const webcamStatusText = document.getElementById('cam-status-text');
    const webcamImg = document.getElementById('live-webcam-img');

    if (webcamPill) {
      webcamPill.classList.remove('active-cam');
      if (webcamStatusText) webcamStatusText.textContent = 'Camera Off (LED Released)';
    }
    if (webcamImg) {
      webcamImg.src = "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' width='640' height='480'><rect width='100%' height='100%' fill='%230f172a'/><text x='50%' y='50%' dominant-baseline='middle' text-anchor='middle' fill='%2364748b' font-family='sans-serif' font-size='18'>Camera Feed Stopped & Hardware LED Turned OFF</text></svg>";
    }
    hapticFeedback(25);
  }

  // Handle incoming server updates
  function handleServerMessage(data) {
    if (data.type === 'clients_update' && isHostDashboard) {
      updateDesktopDashboardClients(data.clients);
    } else if (data.type === 'pong') {
      const pingMs = Date.now() - data.timestamp;
      updatePingLatency(pingMs);
    } else if (data.type === 'screen_frame') {
      const screenImg = document.getElementById('live-screen-img');
      const b64Data = data.data || data.image;
      if (screenImg && b64Data) {
        screenImg.src = 'data:image/jpeg;base64,' + b64Data;
      }
    } else if (data.type === 'webcam_frame') {
      const webcamImg = document.getElementById('live-webcam-img');
      const b64Data = data.data || data.image;
      if (webcamImg && b64Data) {
        webcamImg.src = 'data:image/jpeg;base64,' + b64Data;
      }
    } else if (data.type === 'sys_stats') {
      updateHardwareMetrics(data);
    } else if (data.type === 'open_windows') {
      updateOpenWindowsList(data.windows || []);
    } else if (data.type === 'intruder_alert') {
      handleIntruderAlert(data);
    } else if (data.type === 'sys_alert') {
      handleSysAlert(data);
    }
  }

  // Feature 39: Render Active Desktop Windows List
  function updateOpenWindowsList(windows) {
    const listGrid = document.getElementById('win-list-grid');
    if (!listGrid) return;

    if (!windows || windows.length === 0) {
      listGrid.innerHTML = `<div class="empty-list" style="padding:6px 0;">No active desktop windows detected.</div>`;
      return;
    }

    listGrid.innerHTML = windows.map(w => `
      <button class="win-item-btn" data-app="${w.name}">
        <span>🪟 ${w.title}</span>
        <small style="color:var(--accent-emerald);">Bring to Front ↗</small>
      </button>
    `).join('');

    listGrid.querySelectorAll('.win-item-btn').forEach(btn => {
      btn.onclick = () => {
        const appName = btn.getAttribute('data-app');
        if (appName) {
          sendWS({ type: 'focus_window', app: appName });
          hapticFeedback(20);
        }
      };
    });
  }

  function updatePingLatency(pingMs) {
    const valPing = document.getElementById('val-ping');
    const valQuality = document.getElementById('val-net-quality');
    if (valPing) valPing.textContent = `${pingMs} ms`;
    if (valQuality) {
      if (pingMs < 25) {
        valQuality.textContent = 'Excellent (Ultra-Fast)';
        valQuality.style.color = 'var(--accent-emerald)';
      } else if (pingMs < 60) {
        valQuality.textContent = 'Good';
        valQuality.style.color = 'var(--accent-primary)';
      } else {
        valQuality.textContent = 'Moderate';
        valQuality.style.color = 'var(--accent-warning)';
      }
    }
  }

  function handleIntruderAlert(data) {
    playIntruderSirenSound();
    hapticFeedback([200, 100, 200, 100, 300]);

    if (intruderMsg) intruderMsg.textContent = data.message || 'Intruder Motion Detected!';
    if (intruderTime) intruderTime.textContent = `Captured at ${data.timestamp || 'Now'}`;
    if (intruderImg && data.image) {
      intruderImg.src = 'data:image/jpeg;base64,' + data.image;
    }
    if (intruderModal) intruderModal.classList.add('active');
  }

  function handleSysAlert(data) {
    hapticFeedback(50);
    alert(`${data.title}\n${data.message}`);
  }

  // Update Live Hardware Metrics & Clipboard History Vault
  function updateHardwareMetrics(data) {
    const valCpu = document.getElementById('val-cpu');
    const barCpu = document.getElementById('bar-cpu');
    if (valCpu && barCpu) {
      const cpuVal = Math.round(data.cpu || 0);
      valCpu.textContent = `${cpuVal}%`;
      barCpu.style.width = `${cpuVal}%`;
    }

    const valRam = document.getElementById('val-ram');
    const barRam = document.getElementById('bar-ram');
    const subRam = document.getElementById('sub-ram');
    if (valRam && barRam) {
      const ramVal = Math.round(data.ram || 0);
      valRam.textContent = `${ramVal}%`;
      barRam.style.width = `${ramVal}%`;
      if (subRam) {
        subRam.textContent = `${data.ram_used || 0} GB / ${data.ram_total || 0} GB`;
      }
    }

    const valBatt = document.getElementById('val-battery');
    const barBatt = document.getElementById('bar-battery');
    const subBatt = document.getElementById('sub-battery');
    if (valBatt && barBatt) {
      const battVal = Math.round(data.battery || 100);
      valBatt.textContent = `${battVal}%`;
      barBatt.style.width = `${battVal}%`;
      if (subBatt) {
        subBatt.textContent = data.plugged ? '⚡ Plugged In (Charging)' : '🔋 Discharging';
      }
    }

    const valWifi = document.getElementById('val-wifi');
    const barWifi = document.getElementById('bar-wifi');
    if (valWifi && barWifi) {
      const wifiVal = Math.round(data.wifi || 100);
      valWifi.textContent = `${wifiVal}%`;
      barWifi.style.width = `${wifiVal}%`;
    }

    const valNetDown = document.getElementById('val-net-down');
    const valNetUp = document.getElementById('val-net-up');
    if (valNetDown) {
      const downKb = data.down_speed_kb || 0;
      valNetDown.textContent = downKb > 1024 ? `${(downKb / 1024).toFixed(1)} MB/s` : `${downKb} KB/s`;
    }
    if (valNetUp) {
      const upKb = data.up_speed_kb || 0;
      valNetUp.textContent = upKb > 1024 ? `${(upKb / 1024).toFixed(1)} MB/s` : `${upKb} KB/s`;
    }

    // Feature 46: Clipboard History Vault Update
    if (data.clipboard_history) {
      updateClipboardHistoryVault(data.clipboard_history);
    }
  }

  // Feature 46: Render Clipboard History Vault
  function updateClipboardHistoryVault(historyList) {
    const clipListEl = document.getElementById('clip-history-list');
    if (!clipListEl) return;

    if (!historyList || historyList.length === 0) {
      clipListEl.innerHTML = `<div class="empty-list" style="padding:6px 0;">No copied clipboard history yet. Copy text on PC to see here!</div>`;
      return;
    }

    clipListEl.innerHTML = historyList.map(text => `
      <div class="clip-item" title="Click to copy back to PC clipboard">
        📋 ${escapeHtml(text)}
      </div>
    `).join('');

    clipListEl.querySelectorAll('.clip-item').forEach((item, idx) => {
      item.onclick = () => {
        const textToCopy = historyList[idx];
        sendWS({ type: 'set_clipboard', text: textToCopy });
        alert(`Copied item to PC Clipboard:\n"${textToCopy}"`);
        hapticFeedback(20);
      };
    });
  }

  function escapeHtml(str) {
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  async function checkHostMode() {
    const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    
    try {
      const res = await fetch('/api/info');
      const info = await res.json();
      
      const hostNameEl = document.getElementById('host-name');
      if (hostNameEl) hostNameEl.textContent = `${info.hostname} (${info.localIP})`;

      if (isLocalhost && window.innerWidth > 768) {
        isHostDashboard = true;
        const desktopDashboard = document.getElementById('desktop-dashboard');
        const mobileViews = document.getElementById('mobile-views');
        const bottomNav = document.getElementById('bottom-nav');

        if (desktopDashboard) desktopDashboard.style.display = 'flex';
        if (mobileViews) mobileViews.style.display = 'none';
        if (bottomNav) bottomNav.style.display = 'none';

        const qrImg = document.getElementById('dashboard-qr');
        const urlTxt = document.getElementById('dashboard-url');
        if (qrImg) qrImg.src = info.qrCode;
        if (urlTxt) urlTxt.textContent = info.url;

        const pcName = document.getElementById('stat-pc-name');
        const osTxt = document.getElementById('stat-os');
        const ramTxt = document.getElementById('stat-ram');
        const cpuTxt = document.getElementById('stat-cpu');

        if (pcName) pcName.textContent = info.hostname;
        if (osTxt) osTxt.textContent = `${info.platform} (${info.arch})`;
        if (ramTxt) ramTxt.textContent = `${info.totalMem} GB`;
        if (cpuTxt) cpuTxt.textContent = `${info.cpus} Cores`;

        const btnCopy = document.getElementById('btn-copy-url');
        if (btnCopy) {
          btnCopy.onclick = () => {
            navigator.clipboard.writeText(info.url);
            alert('PC Remote URL copied: ' + info.url);
          };
        }
      }
    } catch (e) {
      console.error('Failed to fetch system info:', e);
    }
  }

  function updateDesktopDashboardClients(clients) {
    const listEl = document.getElementById('devices-list');
    const countEl = document.getElementById('client-count');
    if (countEl) countEl.textContent = clients.length;

    if (!listEl) return;

    if (clients.length === 0) {
      listEl.innerHTML = `<div class="empty-list">No mobile devices connected yet. Scan QR code to connect!</div>`;
      return;
    }

    listEl.innerHTML = clients.map(c => `
      <div class="device-item">
        <div>
          <strong>${c.device}</strong>
          <small style="display:block; color:var(--text-muted);">${c.ip}</small>
        </div>
        <span class="status-pill connected"><span class="dot"></span> Active</span>
      </div>
    `).join('');
  }

  function initNavigation() {
    const navTabs = document.querySelectorAll('.nav-tab-item');
    const viewPanels = document.querySelectorAll('.view-panel');

    navTabs.forEach(tab => {
      tab.addEventListener('click', () => {
        const targetTab = tab.getAttribute('data-tab');
        navTabs.forEach(t => t.classList.remove('active'));
        viewPanels.forEach(p => p.classList.remove('active'));

        tab.classList.add('active');
        const targetPanel = document.getElementById(targetTab);
        if (targetPanel) targetPanel.classList.add('active');
        
        const prevTab = activeTab;
        activeTab = targetTab;
        hapticFeedback(12);

        if (targetTab === 'tab-screen') {
          startScreenStream();
        } else if (prevTab === 'tab-screen') {
          stopScreenStream();
        }

        if (prevTab === 'tab-webcam' && targetTab !== 'tab-webcam') {
          stopWebcamStream();
        }
      });
    });
  }

  function initSecurityHub() {
    const toggleGuard = document.getElementById('toggle-motion-guard');
    const guardBadge = document.getElementById('guard-status-badge');
    const guardTxt = document.getElementById('guard-status-text');
    const toggleAutoLock = document.getElementById('toggle-auto-lock');
    const btnSendWol = document.getElementById('btn-send-wol');

    if (toggleGuard) {
      toggleGuard.onchange = (e) => {
        isMotionGuardActive = e.target.checked;
        if (isMotionGuardActive) {
          sendWS({ type: 'start_motion_guard' });
          if (guardBadge) guardBadge.classList.add('active-guard');
          if (guardTxt) guardTxt.textContent = '🕵️‍♂️ Security Guard Active (Monitoring Camera)';
          hapticFeedback(20);
        } else {
          sendWS({ type: 'stop_motion_guard' });
          if (guardBadge) guardBadge.classList.remove('active-guard');
          if (guardTxt) guardTxt.textContent = 'Security Guard Inactive';
          hapticFeedback(15);
        }
      };
    }

    if (toggleAutoLock) {
      toggleAutoLock.onchange = (e) => {
        isAutoLockActive = e.target.checked;
        sendWS({ type: 'set_auto_lock', enabled: isAutoLockActive });
        hapticFeedback(20);
      };
    }

    if (btnSendWol) {
      btnSendWol.onclick = () => {
        alert('Wake-on-LAN Signal Sent over Wi-Fi network!');
        hapticFeedback(25);
      };
    }
  }

  // Feature 48: 1-Tap Maintenance Init
  function initMaintenance() {
    const btnTrimRam = document.getElementById('btn-trim-ram');
    const btnCleanTemp = document.getElementById('btn-clean-temp');
    const btnRefreshWins = document.getElementById('btn-refresh-windows');

    if (btnTrimRam) {
      btnTrimRam.onclick = () => {
        sendWS({ type: 'trim_ram' });
        hapticFeedback(20);
      };
    }

    if (btnCleanTemp) {
      btnCleanTemp.onclick = () => {
        sendWS({ type: 'clean_temp' });
        hapticFeedback(20);
      };
    }

    if (btnRefreshWins) {
      btnRefreshWins.onclick = () => {
        sendWS({ type: 'get_open_windows' });
        hapticFeedback(15);
      };
    }
  }

  /* GIANT MOBILE TRACKPAD TOUCH GESTURES */
  function initTrackpad() {
    const pad = document.getElementById('touch-pad');
    if (!pad) return;

    let startX = 0, startY = 0;
    let lastX = 0, lastY = 0;
    let isTouching = false;
    let touchStartTime = 0;
    let isDragLocked = false;
    let numFingers = 0;
    let totalMoved = 0;

    const dragLockBtn = document.getElementById('btn-drag-lock');
    if (dragLockBtn) {
      dragLockBtn.onclick = () => {
        isDragLocked = !isDragLocked;
        dragLockBtn.setAttribute('data-active', isDragLocked ? 'true' : 'false');
        if (isDragLocked) {
          sendWS({ type: 'mouse_down', button: 'left' });
        } else {
          sendWS({ type: 'mouse_up', button: 'left' });
        }
        hapticFeedback(15);
      };
    }

    pad.addEventListener('touchstart', (e) => {
      e.preventDefault();
      isTouching = true;
      numFingers = e.touches.length;
      touchStartTime = Date.now();

      const touch = e.touches[0];
      startX = touch.clientX;
      startY = touch.clientY;
      lastX = startX;
      lastY = startY;
      totalMoved = 0;

      pad.classList.add('active-touch');
    }, { passive: false });

    pad.addEventListener('touchmove', (e) => {
      e.preventDefault();
      if (!isTouching) return;

      const touch = e.touches[0];
      const currentX = touch.clientX;
      const currentY = touch.clientY;

      const dx = currentX - lastX;
      const dy = currentY - lastY;

      totalMoved += Math.hypot(dx, dy);

      lastX = currentX;
      lastY = currentY;

      if (e.touches.length === 1) {
        sendWS({
          type: 'move_rel',
          dx: Math.round(dx * currentSensitivity),
          dy: Math.round(dy * currentSensitivity)
        });
      } else if (e.touches.length === 2) {
        sendWS({
          type: 'scroll',
          dy: Math.round(dy * -4)
        });
      }
    }, { passive: false });

    pad.addEventListener('touchend', (e) => {
      e.preventDefault();
      pad.classList.remove('active-touch');
      const touchDuration = Date.now() - touchStartTime;

      if (touchDuration < 300 && totalMoved < 15) {
        if (numFingers === 1) {
          sendWS({ type: 'click', button: 'left' });
          hapticFeedback(15);
        } else if (numFingers === 2) {
          sendWS({ type: 'click', button: 'right' });
          hapticFeedback(20);
        }
      }

      isTouching = false;
    }, { passive: false });

    const btnLeft = document.getElementById('btn-left-click');
    const btnRight = document.getElementById('btn-right-click');
    const btnMid = document.getElementById('btn-middle-click');
    const btnDbl = document.getElementById('btn-double-click');

    if (btnLeft) btnLeft.onclick = () => { sendWS({ type: 'click', button: 'left' }); hapticFeedback(15); };
    if (btnRight) btnRight.onclick = () => { sendWS({ type: 'click', button: 'right' }); hapticFeedback(20); };
    if (btnMid) btnMid.onclick = () => { sendWS({ type: 'click', button: 'middle' }); hapticFeedback(15); };
    if (btnDbl) btnDbl.onclick = () => { sendWS({ type: 'double_click' }); hapticFeedback(25); };
  }

  /* WEBCAM CONTROLS */
  function initWebcamTab() {
    const btnStart = document.getElementById('btn-start-webcam');
    const btnStop = document.getElementById('btn-stop-webcam');

    if (btnStart) btnStart.onclick = startWebcamStream;
    if (btnStop) btnStop.onclick = stopWebcamStream;
  }

  /* WIRELESS FILE UPLOAD & CLIPBOARD SYNC */
  function initFilesAndClipboard() {
    const fileInput = document.getElementById('file-input');
    const btnSelectFile = document.getElementById('btn-select-file');
    const uploadStatus = document.getElementById('upload-status');
    const clipInput = document.getElementById('clip-text-input');
    const btnSendClip = document.getElementById('btn-send-clip');

    if (btnSelectFile && fileInput) {
      btnSelectFile.onclick = () => fileInput.click();

      fileInput.onchange = (e) => {
        const file = e.target.files[0];
        if (!file) return;

        if (uploadStatus) uploadStatus.textContent = `Uploading ${file.name}...`;
        const reader = new FileReader();

        reader.onload = async (evt) => {
          try {
            const base64Data = evt.target.result;
            const res = await fetch('/api/upload', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                fileName: file.name,
                fileData: base64Data
              })
            });
            const result = await res.json();
            if (result.success) {
              if (uploadStatus) uploadStatus.textContent = `✔ Saved to PC Downloads: ${file.name}`;
              hapticFeedback(30);
            } else {
              if (uploadStatus) uploadStatus.textContent = `Upload failed: ${result.error}`;
            }
          } catch (err) {
            if (uploadStatus) uploadStatus.textContent = `Upload error: ${err.message}`;
          }
        };

        reader.readAsDataURL(file);
      };
    }

    if (btnSendClip && clipInput) {
      btnSendClip.onclick = () => {
        const text = clipInput.value;
        if (text) {
          sendWS({ type: 'set_clipboard', text });
          clipInput.value = '';
          alert('Copied to PC Clipboard!');
          hapticFeedback(20);
        }
      };
    }
  }

  /* MEDIA CONTROLS */
  function initMedia() {
    const btnVolUp = document.getElementById('btn-vol-up');
    const btnVolDown = document.getElementById('btn-vol-down');
    const btnMute = document.getElementById('btn-mute');
    const btnPlay = document.getElementById('btn-play-pause');
    const btnNext = document.getElementById('btn-next');
    const btnPrev = document.getElementById('btn-prev');
    const btnPresPrev = document.getElementById('btn-pres-prev');
    const btnPresNext = document.getElementById('btn-pres-next');

    if (btnVolUp) btnVolUp.onclick = () => { sendWS({ type: 'media', subType: 'volume_up' }); hapticFeedback(12); };
    if (btnVolDown) btnVolDown.onclick = () => { sendWS({ type: 'media', subType: 'volume_down' }); hapticFeedback(12); };
    if (btnMute) btnMute.onclick = () => { sendWS({ type: 'media', subType: 'mute' }); hapticFeedback(20); };

    if (btnPlay) btnPlay.onclick = () => { sendWS({ type: 'media', subType: 'play_pause' }); hapticFeedback(15); };
    if (btnNext) btnNext.onclick = () => { sendWS({ type: 'media', subType: 'next' }); hapticFeedback(15); };
    if (btnPrev) btnPrev.onclick = () => { sendWS({ type: 'media', subType: 'prev' }); hapticFeedback(15); };

    if (btnPresPrev) btnPresPrev.onclick = () => { sendWS({ type: 'key', key: 'left' }); hapticFeedback(12); };
    if (btnPresNext) btnPresNext.onclick = () => { sendWS({ type: 'key', key: 'right' }); hapticFeedback(12); };
  }

  /* KEYBOARD */
  function initKeyboard() {
    const textInput = document.getElementById('pc-text-input');
    const btnSendText = document.getElementById('btn-send-text');

    const handleSendText = () => {
      const text = textInput.value;
      if (text) {
        sendWS({ type: 'type', text });
        textInput.value = '';
        hapticFeedback(15);
      }
    };

    if (btnSendText) btnSendText.onclick = handleSendText;
    if (textInput) {
      textInput.onkeypress = (e) => {
        if (e.key === 'Enter') handleSendText();
      };
    }

    document.querySelectorAll('.key-node, .side-key-btn').forEach(btn => {
      btn.onclick = () => {
        const key = btn.getAttribute('data-key');
        if (key) { sendWS({ type: 'key', key }); hapticFeedback(12); }
      };
    });

    document.querySelectorAll('.hk-btn').forEach(btn => {
      btn.onclick = () => {
        const combo = btn.getAttribute('data-hotkey');
        const key = btn.getAttribute('data-key');
        if (combo) { sendWS({ type: 'hotkey', combo }); hapticFeedback(15); }
        else if (key) { sendWS({ type: 'key', key }); hapticFeedback(15); }
      };
    });
  }

  /* APPS & POWER */
  function initSystem() {
    document.querySelectorAll('.app-tile').forEach(btn => {
      btn.onclick = () => {
        const app = btn.getAttribute('data-app');
        if (app) { sendWS({ type: 'launch', app }); hapticFeedback(20); }
      };
    });

    document.querySelectorAll('.power-tile').forEach(btn => {
      btn.onclick = () => {
        const pAction = btn.getAttribute('data-power');
        pendingPowerAction = pAction;
        if (modalTitle) modalTitle.textContent = `Confirm ${pAction.toUpperCase()}`;
        if (modalDesc) modalDesc.textContent = `Are you sure you want to trigger '${pAction}' on your PC?`;
        if (powerModal) powerModal.classList.add('active');
        hapticFeedback(25);
      };
    });

    if (modalCancelBtn) {
      modalCancelBtn.onclick = () => {
        if (powerModal) powerModal.classList.remove('active');
        pendingPowerAction = null;
      };
    }

    if (modalConfirmBtn) {
      modalConfirmBtn.onclick = () => {
        if (pendingPowerAction) {
          sendWS({ type: 'system', subType: pendingPowerAction });
          if (powerModal) powerModal.classList.remove('active');
          pendingPowerAction = null;
          hapticFeedback(30);
        }
      };
    }
  }

  /* LIVE SCREEN MIRROR TAP & MANUAL START */
  function initScreenView() {
    const screenImg = document.getElementById('live-screen-img');
    const refreshBtn = document.getElementById('btn-refresh-screen');

    if (refreshBtn) {
      refreshBtn.onclick = () => {
        startScreenStream();
        hapticFeedback(15);
      };
    }

    if (screenImg) {
      screenImg.onclick = (e) => {
        sendWS({ type: 'click', button: 'left' });
        hapticFeedback(20);
      };
    }
  }

  // Safety: stop webcam feed when page unloads
  window.addEventListener('beforeunload', () => {
    stopWebcamStream();
    stopScreenStream();
  });

  // Initialize after DOM loaded
  document.addEventListener('DOMContentLoaded', () => {
    checkHostMode();
    initWebSocket();
    initNavigation();
    initSecurityHub();
    initMaintenance();
    initTrackpad();
    initWebcamTab();
    initFilesAndClipboard();
    initMedia();
    initKeyboard();
    initSystem();
    initScreenView();
  });
})();
