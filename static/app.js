/** Pulse Remote - Enhanced Mobile Controller */
(function () {
  let ws = null;
  let sessionToken = localStorage.getItem("pulse_session_token");
  let pcDeviceName = "Windows PC";
  let isConnected = false;
  let sensitivity = parseFloat(localStorage.getItem("pulse_sens") || "1.0");
  let activeTab = "trackpad";
  
  // Screen & Camera State
  let isScreenStreaming = false;
  let isWebcamStreaming = false;
  let monitorsList = [];
  let selectedMonitorId = 1;
  let isFindPcRinging = false;
  let statsInterval = null;
  let reconnectAttempts = 0;
  let currentBrowsePath = "";

  // Custom Remotes State
  let customButtons = JSON.parse(localStorage.getItem("pulse_custom_buttons") || "[]");
  if (customButtons.length === 0) {
    customButtons = [
      { id: "1", name: "VS Code", icon: "💻", type: "app", target: "vscode" },
      { id: "2", name: "Chrome", icon: "🌐", type: "app", target: "chrome" },
      { id: "3", name: "Explorer", icon: "📁", type: "app", target: "explorer" },
      { id: "4", name: "Lock PC", icon: "🔒", type: "action", target: "lock" },
    ];
  }

  function vibrate(ms = 15) {
    if (navigator.vibrate) {
      try { navigator.vibrate(ms); } catch (e) {}
    }
  }

  function showToast(msg, type = "info") {
    let container = document.getElementById("toast-container");
    if (!container) {
      container = document.createElement("div");
      container.id = "toast-container";
      container.className = "toast-container";
      document.body.appendChild(container);
    }
    const toast = document.createElement("div");
    toast.className = `toast-item toast-${type}`;
    toast.textContent = msg;
    container.appendChild(toast);
    setTimeout(() => {
      toast.classList.add("toast-fadeout");
      setTimeout(() => toast.remove(), 350);
    }, 2800);
  }

  const pairingScreen = document.getElementById("pairing-screen");
  const appContainer = document.getElementById("app-container");
  const pairStatusText = document.getElementById("pair-status-text");
  const connectedPcName = document.getElementById("connected-pc-name");
  const latencyBadge = document.getElementById("latency-badge");
  const manualPairBox = document.getElementById("manual-pair-box");

  window.addEventListener("DOMContentLoaded", () => {
    setupMainTabs();
    setupSubPills();
    setupTrackpad();
    setupKeysAndShortcuts();
    setupScreenViewer();
    setupWebcam();
    setupMediaControls();
    setupFileManager();
    setupClipboard();
    setupDashboard();
    setupCustomButtons();
    setupEmergencyLock();
    setupBossKey();
    setupBrightnessControl();
    setupSecurityControls();
    setupLiveHUDLoop();

    const urlParams = new URLSearchParams(window.location.search);
    const pairToken = urlParams.get("pair");

    if (pairToken) {
      pairStatusText.textContent = "Pairing with PC...";
      performPairing(pairToken);
    } else if (sessionToken) {
      pairStatusText.textContent = "Connecting to PC...";
      connectWebSocket();
    } else {
      pairStatusText.textContent = "Scan QR code or enter token:";
      manualPairBox.style.display = "block";
    }

    document.getElementById("manual-pair-btn")?.addEventListener("click", () => {
      const manualToken = document.getElementById("manual-token-input").value.trim();
      if (manualToken) performPairing(manualToken);
    });
  });

  async function performPairing(token) {
    try {
      const res = await fetch("/api/pair", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          pairing_token: token,
          device_id: "phone-" + Math.random().toString(36).substring(2, 8),
          name: navigator.userAgent.includes("iPhone") ? "iPhone" : (navigator.userAgent.includes("Android") ? "Android Phone" : "Mobile Client")
        })
      });
      const data = await res.json();
      if (data.success && data.session_token) {
        sessionToken = data.session_token;
        localStorage.setItem("pulse_session_token", sessionToken);
        pcDeviceName = data.device_name || "Windows PC";
        window.history.replaceState({}, document.title, window.location.pathname);
        connectWebSocket();
      } else {
        showPairError(data.error || "Pairing token expired or invalid.");
      }
    } catch (err) {
      showPairError("Unable to connect. Ensure phone is on the same Wi-Fi as PC.");
    }
  }

  function showPairError(msg) {
    pairStatusText.textContent = msg;
    manualPairBox.style.display = "block";
  }

  function connectWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      reconnectAttempts = 0;
      ws.send(JSON.stringify({ event: "auth", data: { session_token: sessionToken } }));
    };

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        handleServerMessage(msg);
      } catch (err) {}
    };

    ws.onclose = () => {
      isConnected = false;
      reconnectAttempts++;
      latencyBadge.textContent = `Reconnecting (${reconnectAttempts})...`;
      setTimeout(() => {
        if (sessionToken) connectWebSocket();
      }, Math.min(5000, 1000 * reconnectAttempts));
    };

    ws.onerror = () => { ws.close(); };
  }

  function sendWS(event, data = {}) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ event, data }));
    }
  }
  function handleServerMessage(msg) {
    const { event, data } = msg;

    if (event === "auth_success") {
      isConnected = true;
      pairingScreen.classList.add("hidden");
      appContainer.classList.remove("hidden");
      pcDeviceName = data.device_name || "Windows PC";
      connectedPcName.textContent = pcDeviceName;
      latencyBadge.textContent = "🟢 Direct Wi-Fi";

      sendWS("monitors:list");
      sendWS("app:list");
      sendWS("custom_remotes:get");
      if (activeTab === "files") fetchFileList();
      if (activeTab === "system") refreshSystemData();
    } else if (event === "auth_error") {
      localStorage.removeItem("pulse_session_token");
      sessionToken = null;
      pairingScreen.classList.remove("hidden");
      appContainer.classList.add("hidden");
      showPairError("Session expired. Please scan a new QR code.");
    } else if (event === "permission_denied") {
      alert(`⚠️ ${data.message}`);
    } else if (event === "screen:frame_data") {
      renderScreenFrame(data.frame);
    } else if (event === "webcam:frame_data") {
      renderWebcamFrame(data.frame);
    } else if (event === "monitors:list_data") {
      renderMonitors(data.monitors);
    } else if (event === "app:list_data") {
      renderQuickActions(data.apps);
    } else if (event === "app:launch_result") {
      vibrate(20);
      alert(data.message);
    } else if (event === "find_pc:status") {
      updateFindPcStatus(data.success, data.message);
    } else if (event === "clipboard:data") {
      document.getElementById("clip-pc-text").value = data.text || "";
      renderClipboardHistory(data.history || []);
    } else if (event === "clipboard:updated") {
      vibrate(15);
      alert("✅ Text copied to PC Clipboard!");
    } else if (event === "clipboard:cleared") {
      vibrate(15);
      document.getElementById("clip-pc-text").value = "";
      alert("PC Clipboard cleared.");
    } else if (event === "system:stats_data") {
      renderSystemStats(data);
    } else if (event === "system:action_result") {
      vibrate(30);
      showToast(data.message, data.success ? "success" : "error");
    } else if (event === "system:panic_result") {
      vibrate([50, 50, 100]);
      showToast(data.message, "error");
    } else if (event === "brightness:changed") {
      updateBrightnessUI(data.level);
    } else if (event === "guard:status") {
      vibrate(20);
      showToast(data.message, data.active ? "success" : "info");
      const chk = document.getElementById("toggle-cctv-guard");
      if (chk) chk.checked = data.active;
    } else if (event === "guard:intruder_alert") {
      handleIntruderAlert(data);
    } else if (event === "settings:walkaway_status") {
      vibrate(15);
      showToast(`Walk-Away Auto-Lock ${data.enabled ? "Enabled" : "Disabled"}`, "info");
      const chk = document.getElementById("toggle-walkaway-lock");
      if (chk) chk.checked = data.enabled;
    } else if (event === "files:list_data") {
      renderFileList(data);
    } else if (event === "devices:list_data") {
      renderPairedDevices(data.devices);
    } else if (event === "devices:perms_updated") {
      vibrate(15);
      alert("Permissions updated!");
    } else if (event === "devices:revoked") {
      vibrate(20);
      sendWS("devices:list");
    } else if (event === "devices:all_revoked") {
      alert("All devices disconnected.");
      window.location.reload();
    }
  }

  function setupMainTabs() {
    const navButtons = document.querySelectorAll(".nav-btn");
    navButtons.forEach((btn) => {
      btn.addEventListener("click", () => {
        vibrate(10);
        const tab = btn.dataset.tab;
        navButtons.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");

        document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
        document.getElementById(`tab-${tab}`)?.classList.add("active");
        activeTab = tab;

        if (tab !== "screen" && isScreenStreaming) {
          document.getElementById("btn-toggle-stream")?.click();
        }
        if (tab !== "screen" && isWebcamStreaming) {
          document.getElementById("btn-toggle-webcam")?.click();
        }

        if (tab === "screen") sendWS("monitors:list");
        if (tab === "files") fetchFileList();
        if (tab === "system") {
          refreshSystemData();
          if (!statsInterval) statsInterval = setInterval(refreshSystemData, 2000);
        } else {
          if (statsInterval) {
            clearInterval(statsInterval);
            statsInterval = null;
          }
        }
      });
    });
  }

  function setupSubPills() {
    // 1. Remote Sub-Pills (keys, media, presenter, gaming, custom)
    document.querySelectorAll(".sub-pill").forEach((pill) => {
      pill.addEventListener("click", () => {
        vibrate(10);
        document.querySelectorAll(".sub-pill").forEach((p) => p.classList.remove("active"));
        pill.classList.add("active");
        const sub = pill.dataset.sub;
        document.querySelectorAll(".sub-panel").forEach((p) => p.classList.remove("active"));
        document.getElementById(`sub-${sub}`)?.classList.add("active");
      });
    });

    // 2. Live View Sub-Pills (screen, webcam)
    document.querySelectorAll(".view-pill").forEach((pill) => {
      pill.addEventListener("click", () => {
        vibrate(10);
        document.querySelectorAll(".view-pill").forEach((p) => p.classList.remove("active"));
        pill.classList.add("active");
        const view = pill.dataset.view;
        document.querySelectorAll(".view-panel").forEach((p) => p.classList.remove("active"));
        document.getElementById(`view-${view}`)?.classList.add("active");
      });
    });

    // 3. Files Sub-Pills (files, clipboard)
    document.querySelectorAll(".file-pill").forEach((pill) => {
      pill.addEventListener("click", () => {
        vibrate(10);
        document.querySelectorAll(".file-pill").forEach((p) => p.classList.remove("active"));
        pill.classList.add("active");
        const filetab = pill.dataset.filetab;
        document.querySelectorAll(".file-sub-panel").forEach((p) => p.classList.remove("active"));
        document.getElementById(`filetab-${filetab}`)?.classList.add("active");
        if (filetab === "clipboard") sendWS("clipboard:get");
      });
    });
  }

  function refreshSystemData() {
    sendWS("system:stats");
    sendWS("devices:list");
  }
  function setupTrackpad() {
    const surface = document.getElementById("touch-surface");
    const pointer = document.getElementById("virtual-pointer");

    // Speed selector buttons
    document.querySelectorAll(".btn-speed").forEach((btn) => {
      btn.addEventListener("click", () => {
        vibrate(10);
        document.querySelectorAll(".btn-speed").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        sensitivity = parseFloat(btn.dataset.sens || "1.0");
        localStorage.setItem("pulse_sens", sensitivity.toString());
      });
    });

    let lastX = 0;
    let lastY = 0;
    let touchStartTime = 0;
    let hasMoved = false;

    surface.addEventListener("touchstart", (e) => {
      touchStartTime = Date.now();
      hasMoved = false;
      if (e.touches.length === 1) {
        lastX = e.touches[0].clientX;
        lastY = e.touches[0].clientY;
        const rect = surface.getBoundingClientRect();
        pointer.style.left = (lastX - rect.left) + "px";
        pointer.style.top = (lastY - rect.top) + "px";
        pointer.style.display = "block";
      } else if (e.touches.length === 2) {
        lastY = e.touches[0].clientY;
      }
    }, { passive: false });

    surface.addEventListener("touchmove", (e) => {
      e.preventDefault();
      if (e.touches.length === 1) {
        const curX = e.touches[0].clientX;
        const curY = e.touches[0].clientY;
        const dx = curX - lastX;
        const dy = curY - lastY;
        if (Math.abs(dx) > 1.0 || Math.abs(dy) > 1.0) {
          hasMoved = true;
          sendWS("mouse:move", { dx, dy, sensitivity });
        }
        lastX = curX;
        lastY = curY;
        const rect = surface.getBoundingClientRect();
        pointer.style.left = Math.max(10, Math.min(rect.width - 10, curX - rect.left)) + "px";
        pointer.style.top = Math.max(10, Math.min(rect.height - 10, curY - rect.top)) + "px";
      } else if (e.touches.length === 2) {
        const curY = e.touches[0].clientY;
        const dy = (curY - lastY) / 7;
        if (Math.abs(dy) > 0.4) {
          hasMoved = true;
          sendWS("mouse:scroll", { dy });
        }
        lastY = curY;
      }
    }, { passive: false });

    surface.addEventListener("touchend", (e) => {
      const duration = Date.now() - touchStartTime;
      pointer.style.display = "none";
      if (!hasMoved && duration < 250) {
        if (e.changedTouches.length === 1) {
          vibrate(10);
          sendWS("mouse:click", { button: "left" });
        }
      }
    });

    document.getElementById("btn-left-click")?.addEventListener("click", () => { vibrate(15); sendWS("mouse:click", { button: "left" }); });
    document.getElementById("btn-middle-click")?.addEventListener("click", () => { vibrate(15); sendWS("mouse:click", { button: "middle" }); });
    document.getElementById("btn-right-click")?.addEventListener("click", () => { vibrate(15); sendWS("mouse:click", { button: "right" }); });
    document.getElementById("btn-scroll-up")?.addEventListener("click", () => { vibrate(10); sendWS("mouse:scroll", { dy: 2 }); });
    document.getElementById("btn-scroll-down")?.addEventListener("click", () => { vibrate(10); sendWS("mouse:scroll", { dy: -2 }); });
  }

  function setupKeysAndShortcuts() {
    const typeForm = document.getElementById("type-form");
    const typeInput = document.getElementById("type-text-input");

    typeForm?.addEventListener("submit", (e) => {
      e.preventDefault();
      const text = typeInput.value;
      if (text) {
        vibrate(15);
        sendWS("keyboard:type", { text });
        typeInput.value = "";
      }
    });

    document.querySelectorAll(".btn-tile, .btn-key-tile").forEach((btn) => {
      btn.addEventListener("click", () => {
        vibrate(15);
        const sc = btn.dataset.shortcut;
        const k = btn.dataset.key;
        if (sc) sendWS("keyboard:shortcut", { shortcut: sc });
        if (k) sendWS("keyboard:key", { key: k });
      });
    });

    document.querySelectorAll(".btn-huge-slide").forEach((btn) => {
      btn.addEventListener("click", () => {
        vibrate(20);
        const sc = btn.dataset.shortcut;
        if (sc) sendWS("keyboard:shortcut", { shortcut: sc });
      });
    });

    document.querySelectorAll(".btn-dpad-key, .btn-action-pad").forEach((btn) => {
      btn.addEventListener("click", () => {
        vibrate(15);
        const k = btn.dataset.key;
        if (k) sendWS("keyboard:key", { key: k });
      });
    });
  }

  function setupScreenViewer() {
    const btnToggle = document.getElementById("btn-toggle-stream");
    const screenImg = document.getElementById("screen-img");
    const placeholder = document.getElementById("screen-placeholder");
    const viewport = document.getElementById("screen-viewport");
    const touchRipple = document.getElementById("touch-ripple");

    btnToggle?.addEventListener("click", () => {
      vibrate(15);
      isScreenStreaming = !isScreenStreaming;
      if (isScreenStreaming) {
        btnToggle.textContent = "⏹ Stop";
        btnToggle.style.background = "#f43f5e";
        screenImg.classList.remove("hidden");
        placeholder.classList.add("hidden");
        pullScreenFrame();
      } else {
        btnToggle.textContent = "▶ Start Stream";
        btnToggle.style.background = "";
        screenImg.classList.add("hidden");
        placeholder.classList.remove("hidden");
      }
    });

    function pullScreenFrame() {
      if (isScreenStreaming && activeTab === "screen") {
        sendWS("screen:frame", { quality: 60, maxWidth: 1280, monitor_id: selectedMonitorId });
      }
    }

    window.renderScreenFrame = (frameB64) => {
      screenImg.src = frameB64;
      if (isScreenStreaming && activeTab === "screen") {
        setTimeout(pullScreenFrame, 60);
      }
    };

    // Touch-to-click mapping on selected monitor with visual touch ripple effect
    screenImg.addEventListener("click", (e) => {
      const rect = screenImg.getBoundingClientRect();
      const clickX = e.clientX - rect.left;
      const clickY = e.clientY - rect.top;
      const relX = clickX / rect.width;
      const relY = clickY / rect.height;

      // Show visual touch ripple
      if (touchRipple) {
        touchRipple.style.left = `${clickX}px`;
        touchRipple.style.top = `${clickY}px`;
        touchRipple.classList.remove("active");
        void touchRipple.offsetWidth;
        touchRipple.classList.add("active");
      }

      if (relX >= 0 && relX <= 1 && relY >= 0 && relY <= 1) {
        vibrate(20);
        sendWS("mouse:click_rel", {
          rel_x: relX,
          rel_y: relY,
          monitor_id: selectedMonitorId,
          button: "left"
        });
      }
    });

    document.getElementById("btn-screen-fs")?.addEventListener("click", () => {
      vibrate(15);
      if (!document.fullscreenElement) {
        viewport.requestFullscreen().catch(() => {});
      } else {
        document.exitFullscreen().catch(() => {});
      }
    });
  }

  function renderMonitors(monitors) {
    monitorsList = monitors;
    const container = document.getElementById("monitors-pill-container");
    if (!container) return;
    container.innerHTML = monitors.map((m) => `
      <button class="btn-mon-pill ${m.id === selectedMonitorId ? 'active' : ''}" onclick="window.selectMonitor(${m.id})">
        ${m.name} (${m.width}×${m.height})
      </button>
    `).join("");
  }

  window.selectMonitor = (monId) => {
    vibrate(15);
    selectedMonitorId = monId;
    sendWS("monitors:select", { monitor_id: monId });
    renderMonitors(monitorsList);
  };

  function setupWebcam() {
    const btnToggle = document.getElementById("btn-toggle-webcam");
    const webcamImg = document.getElementById("webcam-img");
    const placeholder = document.getElementById("webcam-placeholder");

    btnToggle?.addEventListener("click", () => {
      vibrate(15);
      isWebcamStreaming = !isWebcamStreaming;
      if (isWebcamStreaming) {
        btnToggle.textContent = "⏹ Stop";
        btnToggle.style.background = "#f43f5e";
        webcamImg.classList.remove("hidden");
        placeholder.classList.add("hidden");
        pullWebcamFrame();
      } else {
        btnToggle.textContent = "▶ Start Camera";
        btnToggle.style.background = "";
        webcamImg.classList.add("hidden");
        placeholder.classList.remove("hidden");
        sendWS("webcam:stop");
      }
    });

    function pullWebcamFrame() {
      if (isWebcamStreaming && activeTab === "screen") {
        sendWS("webcam:frame", { camera_id: 0, quality: 60 });
      }
    }

    window.renderWebcamFrame = (frameB64) => {
      webcamImg.src = frameB64;
      if (isWebcamStreaming && activeTab === "screen") {
        setTimeout(pullWebcamFrame, 70);
      }
    };
  }

  function setupMediaControls() {
    document.querySelectorAll(".btn-media-round, .btn-media-round-primary, .btn-volume-box").forEach((btn) => {
      btn.addEventListener("click", () => {
        vibrate(20);
        const sc = btn.dataset.shortcut;
        if (sc) sendWS("media:command", { command: sc });
      });
    });
  }
  function setupFileManager() {
    const uploader = document.getElementById("file-uploader");
    const hud = document.getElementById("transfer-hud");
    const hudFile = document.getElementById("transfer-filename");
    const hudPct = document.getElementById("transfer-percent");
    const barFill = document.getElementById("transfer-bar-fill");
    const hudSpeed = document.getElementById("transfer-speed");
    const hudEta = document.getElementById("transfer-eta");

    uploader?.addEventListener("change", (e) => {
      const file = e.target.files[0];
      if (!file) return;
      hud.classList.remove("hidden");
      hudFile.textContent = `Uploading: ${file.name}`;
      
      const formData = new FormData();
      formData.append("file", file);
      const xhr = new XMLHttpRequest();
      const startTime = Date.now();

      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) {
          const percent = Math.round((event.loaded / event.total) * 100);
          hudPct.textContent = `${percent}%`;
          barFill.style.width = `${percent}%`;
          const elapsedSec = (Date.now() - startTime) / 1000 || 0.1;
          const speedMBs = (event.loaded / (1024 * 1024)) / elapsedSec;
          hudSpeed.textContent = `Speed: ${speedMBs.toFixed(1)} MB/s`;
          const remainingBytes = event.total - event.loaded;
          const etaSec = Math.round(remainingBytes / (speedMBs * 1024 * 1024 || 1));
          hudEta.textContent = `ETA: ${etaSec}s`;
        }
      };

      xhr.onload = () => {
        hud.classList.add("hidden");
        vibrate(30);
        if (xhr.status === 200) {
          alert(`✅ "${file.name}" uploaded to PC!`);
          fetchFileList(currentBrowsePath);
        } else {
          alert("Upload failed.");
        }
      };

      xhr.open("POST", `/api/files/upload?dir=${encodeURIComponent(currentBrowsePath || "")}`);
      xhr.setRequestHeader("X-Session-Token", sessionToken);
      xhr.send(formData);
    });
  }

  function fetchFileList(path = "") {
    sendWS("files:list", { path });
  }

  function renderFileList(data) {
    const container = document.getElementById("file-list-container");
    const breadcrumb = document.getElementById("crumb-current-path");
    const quickFolders = document.getElementById("quick-folders");

    currentBrowsePath = data.current_path || "";
    breadcrumb.textContent = currentBrowsePath;

    if (data.quick_folders && quickFolders) {
      quickFolders.innerHTML = data.quick_folders.map(f => `
        <button class="btn-folder-tag" onclick="window.browsePath('${f.path.replace(/\\/g, "/")}')">
          📁 ${f.name}
        </button>
      `).join("");
    }

    if (!data.items || data.items.length === 0) {
      container.innerHTML = `<div class="loading-text">Empty Folder</div>`;
      return;
    }

    let html = "";
    if (data.parent_path) {
      html += `
        <div class="file-item" onclick="window.browsePath('${data.parent_path.replace(/\\/g, "/")}')">
          <div class="file-info">
            <span style="font-size: 20px;">📁</span>
            <span class="file-name" style="font-weight: 800;">.. (Parent Folder)</span>
          </div>
        </div>
      `;
    }

    data.items.forEach((item) => {
      const isDir = item.is_dir;
      const icon = isDir ? "📁" : (item.ext === "pdf" ? "📄" : (["jpg","png","webp"].includes(item.ext) ? "🖼️" : "📦"));
      const sizeStr = isDir ? "" : formatBytes(item.size);
      const cleanPath = item.path.replace(/\\/g, "/");

      if (isDir) {
        html += `
          <div class="file-item" onclick="window.browsePath('${cleanPath}')">
            <div class="file-info">
              <span style="font-size: 20px;">${icon}</span>
              <span class="file-name">${item.name}</span>
            </div>
            <span style="font-size: 11px; color: var(--muted); font-weight: 700;">Folder</span>
          </div>
        `;
      } else {
        html += `
          <div class="file-item">
            <div class="file-info">
              <span style="font-size: 20px;">${icon}</span>
              <span class="file-name">${item.name}</span>
            </div>
            <div class="flex gap-2" style="align-items: center;">
              <span style="font-size: 11px; color: var(--text-muted); font-weight: 700;">${sizeStr}</span>
              <a href="/api/files/download?path=${encodeURIComponent(item.path)}&token=${sessionToken}" download class="btn btn-sm btn-primary" style="padding: 6px 12px; font-size: 11px;">⬇ Save</a>
            </div>
          </div>
        `;
      }
    });

    container.innerHTML = html;
  }

  window.browsePath = (path) => {
    vibrate(10);
    fetchFileList(path);
  };

  function formatBytes(bytes) {
    if (!bytes) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
  }

  function setupClipboard() {
    document.getElementById("btn-get-clipboard")?.addEventListener("click", () => {
      vibrate(15);
      sendWS("clipboard:get");
    });

    document.getElementById("btn-set-clipboard")?.addEventListener("click", () => {
      const text = document.getElementById("clip-phone-text").value;
      if (text) {
        vibrate(15);
        sendWS("clipboard:set", { text });
      }
    });

    document.getElementById("btn-clear-clipboard")?.addEventListener("click", () => {
      vibrate(20);
      if (confirm("Clear PC Clipboard?")) {
        sendWS("clipboard:clear");
      }
    });
  }

  function renderClipboardHistory(history) {
    const container = document.getElementById("clip-history-container");
    if (!container) return;
    if (!history || history.length === 0) {
      container.innerHTML = `<span style="font-size: 12px; color: var(--muted);">No clipboard history</span>`;
      return;
    }
    container.innerHTML = history.map((item) => `
      <div class="clip-chip" onclick="window.useClipHistory('${encodeURIComponent(item)}')">
        ${item.replace(/</g, "&lt;")}
      </div>
    `).join("");
  }

  window.useClipHistory = (encodedItem) => {
    vibrate(15);
    const item = decodeURIComponent(encodedItem);
    document.getElementById("clip-phone-text").value = item;
  };

  function setupDashboard() {
    // Find My PC
    document.getElementById("btn-find-pc-toggle")?.addEventListener("click", () => {
      vibrate(20);
      if (!isFindPcRinging) sendWS("find_pc:start");
      else sendWS("find_pc:stop");
    });

    document.getElementById("btn-revoke-all")?.addEventListener("click", () => {
      vibrate(30);
      if (confirm("Disconnect and revoke all devices?")) {
        sendWS("devices:revoke_all");
      }
    });
  }

  function updateFindPcStatus(success, message) {
    const btn = document.getElementById("btn-find-pc-toggle");
    if (!btn) return;
    if (message.includes("playing") || message.includes("already")) {
      isFindPcRinging = true;
      btn.textContent = "🛑 Stop Sound";
      btn.classList.remove("btn-primary");
      btn.classList.add("btn-danger");
      vibrate(40);
    } else {
      isFindPcRinging = false;
      btn.textContent = "Ring PC";
      btn.classList.remove("btn-danger");
      btn.classList.add("btn-primary");
      vibrate(20);
    }
  }

  function renderQuickActions(apps) {
    const grid = document.getElementById("quick-actions-grid");
    if (!grid) return;
    const badgeColors = {
      chrome: "badge-blue",
      vscode: "badge-cyan",
      explorer: "badge-amber",
      notepad: "badge-green",
      downloads: "badge-purple",
      taskmgr: "badge-orange",
      terminal: "badge-dark",
      calc: "badge-indigo",
      settings: "badge-blue"
    };
    grid.innerHTML = apps.map((app) => {
      const badgeClass = badgeColors[app.key] || "badge-blue";
      return `
        <button class="btn-tile" onclick="window.launchApp('${app.key}')">
          <span class="tile-icon-badge ${badgeClass}">${app.icon}</span>
          <span class="tile-text">${app.name}</span>
        </button>
      `;
    }).join("");
  }

  window.launchApp = (appKey) => {
    vibrate(20);
    sendWS("app:launch", { app_key: appKey });
  };

  let lastBatteryAlert = null;

  function renderSystemStats(data) {
    if (!data) return;

    // 1. CPU
    const cpuEl = document.getElementById("stat-cpu");
    const barCpu = document.getElementById("bar-cpu");
    if (cpuEl) cpuEl.textContent = `${data.cpu_percent}%`;
    if (barCpu) barCpu.style.width = `${data.cpu_percent}%`;

    // 2. RAM
    const ramEl = document.getElementById("stat-ram");
    const barRam = document.getElementById("bar-ram");
    if (ramEl && data.memory) ramEl.textContent = `${data.memory.used_gb} / ${data.memory.total_gb} GB`;
    if (barRam && data.memory) barRam.style.width = `${data.memory.percent}%`;

    // 3. Disk
    const diskEl = document.getElementById("stat-disk");
    const barDisk = document.getElementById("bar-disk");
    if (diskEl && data.disk) {
      diskEl.textContent = `${data.disk.used_gb} / ${data.disk.total_gb} GB`;
      if (barDisk) barDisk.style.width = `${data.disk.percent}%`;
    }

    // 4. Network & CPU Model
    const netEl = document.getElementById("stat-net");
    if (netEl && data.network) {
      netEl.textContent = `▲ ${data.network.upload_kbps} KB/s | ▼ ${data.network.download_kbps} KB/s`;
    }
    const cpuModelEl = document.getElementById("stat-cpu-model");
    if (cpuModelEl) cpuModelEl.textContent = data.cpu_model || "Multi-Core Processor";

    // 5. Battery HUD & Smart Alerts
    const batPercentEl = document.getElementById("stat-battery-percent");
    const barBattery = document.getElementById("bar-battery");
    const batStatusEl = document.getElementById("stat-battery-status");
    const batTimeEl = document.getElementById("stat-battery-time");
    const batIcon = document.getElementById("battery-icon");

    if (data.battery) {
      const pct = data.battery.percent;
      const plugged = data.battery.power_plugged;

      if (batPercentEl) batPercentEl.textContent = `${pct}%`;
      if (barBattery) {
        barBattery.style.width = `${pct}%`;
        if (pct <= 20) barBattery.style.background = "#EF4444";
        else if (pct <= 40) barBattery.style.background = "#F59E0B";
        else barBattery.style.background = "linear-gradient(90deg, #10B981, #06B6D4)";
      }

      if (batIcon) batIcon.textContent = plugged ? "⚡" : (pct <= 20 ? "🪫" : "🔋");
      if (batStatusEl) batStatusEl.textContent = plugged ? "⚡ Charging (AC Adapter Connected)" : "🔋 On Battery Power";

      if (batTimeEl) {
        if (data.battery.secsleft && data.battery.secsleft > 0) {
          const hrs = Math.floor(data.battery.secsleft / 3600);
          const mins = Math.floor((data.battery.secsleft % 3600) / 60);
          batTimeEl.textContent = `~${hrs}h ${mins}m remaining`;
        } else {
          batTimeEl.textContent = plugged ? "AC Connected" : "Calculating...";
        }
      }

      // Smart Battery Alerts
      if (pct >= 99 && plugged && lastBatteryAlert !== "full") {
        lastBatteryAlert = "full";
        vibrate([100, 50, 100, 50, 200]);
        showToast("⚡ Laptop Fully Charged (100%)! Unplug charger to preserve battery health.", "info");
      } else if (pct <= 20 && !plugged && lastBatteryAlert !== "low") {
        lastBatteryAlert = "low";
        vibrate([200, 100, 200]);
        showToast("⚠️ Battery Low (20%)! Connect PC charger now.", "error");
      } else if (pct > 25 && pct < 95) {
        lastBatteryAlert = null;
      }
    } else {
      if (batPercentEl) batPercentEl.textContent = "AC";
      if (barBattery) barBattery.style.width = "100%";
      if (batStatusEl) batStatusEl.textContent = "🔌 Desktop AC Power";
      if (batTimeEl) batTimeEl.textContent = "Unlimited";
    }

    // 6. Sync Toggles
    const toggleWalk = document.getElementById("toggle-walkaway-lock");
    if (toggleWalk && typeof data.walkaway_lock_enabled === "boolean") {
      toggleWalk.checked = data.walkaway_lock_enabled;
    }

    const toggleGuard = document.getElementById("toggle-cctv-guard");
    if (toggleGuard && typeof data.guard_mode_active === "boolean") {
      toggleGuard.checked = data.guard_mode_active;
    }

    // 7. Brightness sync
    if (typeof data.brightness === "number") {
      updateBrightnessUI(data.brightness);
    }

    // 8. Last intruder snapshot
    if (data.last_intruder && data.last_intruder.photo) {
      updateIntruderPreview(data.last_intruder);
    }
  }

  function renderPairedDevices(devices) {
    const container = document.getElementById("paired-devices-container");
    if (!container) return;
    if (!devices || devices.length === 0) {
      container.innerHTML = `<span style="font-size: 12px; color: var(--text-muted);">No paired devices</span>`;
      return;
    }
    container.innerHTML = devices.map(d => `
      <div class="device-card">
        <div class="flex gap-2" style="align-items: center;">
          <span class="status-dot ${d.is_online ? 'online' : ''}"></span>
          <strong style="font-size: 14px;">${d.name}</strong>
          <span style="font-size: 11px; color: var(--text-muted);">(${d.last_seen_str})</span>
        </div>
        <button class="btn btn-sm btn-danger" onclick="window.revokeDevice('${d.device_id}')">Revoke</button>
      </div>
    `).join("");
  }

  window.revokeDevice = (deviceId) => {
    vibrate(20);
    if (confirm("Revoke this device?")) {
      sendWS("devices:revoke", { device_id: deviceId });
    }
  };

  function setupCustomButtons() {
    renderCustomButtons();
    const modal = document.getElementById("modal-add-button");
    document.getElementById("btn-add-custom-btn")?.addEventListener("click", () => { modal.classList.remove("hidden"); });
    document.getElementById("btn-cancel-cust-btn")?.addEventListener("click", () => { modal.classList.add("hidden"); });

    document.getElementById("btn-save-cust-btn")?.addEventListener("click", () => {
      const name = document.getElementById("cust-btn-name").value.trim();
      const icon = document.getElementById("cust-btn-icon").value;
      const type = document.getElementById("cust-btn-action-type").value;
      const target = document.getElementById("cust-btn-target").value.trim();

      if (name && target) {
        vibrate(15);
        customButtons.push({ id: Date.now().toString(), name, icon, type, target });
        localStorage.setItem("pulse_custom_buttons", JSON.stringify(customButtons));
        modal.classList.add("hidden");
        document.getElementById("cust-btn-name").value = "";
        document.getElementById("cust-btn-target").value = "";
        renderCustomButtons();
      }
    });

    window.triggerCustomButton = (btnId) => {
      const btn = customButtons.find(b => b.id === btnId);
      if (btn) {
        vibrate(20);
        if (btn.type === "app") {
          sendWS("app:launch", { app_key: btn.target });
        } else if (btn.type === "action") {
          sendWS("system:action", { action: btn.target });
        } else {
          sendWS("keyboard:shortcut", { shortcut: btn.target });
        }
      }
    };
  }

  function renderCustomButtons() {
    const container = document.getElementById("custom-buttons-container");
    if (!container) return;
    container.innerHTML = customButtons.map((btn) => `
      <button class="btn-tile" onclick="window.triggerCustomButton('${btn.id}')">
        <span class="tile-icon-badge badge-blue">${btn.icon}</span>
        <span class="tile-text">${btn.name}</span>
      </button>
    `).join("");
  }

  function setupEmergencyLock() {
    document.getElementById("btn-emergency-lock")?.addEventListener("click", (e) => {
      e.preventDefault();
      vibrate(40);
      sendWS("system:action", { action: "lock" });
      showToast("🔒 Locking PC...", "info");
    });
  }

  // --- 1. Boss / Panic Key (Anti-Spy) ---
  function setupBossKey() {
    const triggerPanic = (e) => {
      e?.preventDefault();
      vibrate([50, 50, 100]);
      sendWS("system:panic");
      showToast("🚨 Boss Key Triggered: Clearing screen & muting audio!", "error");
    };

    document.getElementById("btn-panic-mode")?.addEventListener("click", triggerPanic);
    document.getElementById("btn-panic-banner")?.addEventListener("click", triggerPanic);
  }

  // --- 2. Screen Brightness Control ---
  let brightnessDebounce = null;
  function setupBrightnessControl() {
    const slider = document.getElementById("brightness-slider");
    const badge = document.getElementById("brightness-val-badge");

    slider?.addEventListener("input", () => {
      const val = parseInt(slider.value, 10);
      if (badge) badge.textContent = `${val}%`;
      clearTimeout(brightnessDebounce);
      brightnessDebounce = setTimeout(() => {
        sendWS("brightness:set", { level: val });
      }, 100);
    });

    document.querySelectorAll(".btn-preset-chip").forEach((btn) => {
      btn.addEventListener("click", () => {
        vibrate(15);
        const val = parseInt(btn.dataset.brightness, 10);
        if (slider) slider.value = val;
        if (badge) badge.textContent = `${val}%`;
        sendWS("brightness:set", { level: val });
      });
    });
  }

  function updateBrightnessUI(level) {
    const slider = document.getElementById("brightness-slider");
    const badge = document.getElementById("brightness-val-badge");
    if (slider && document.activeElement !== slider) slider.value = level;
    if (badge) badge.textContent = `${level}%`;
  }

  // --- 3. Smart Security (Walk-Away Lock & CCTV Intruder Alert) ---
  function setupSecurityControls() {
    // Walk-Away Auto-Lock
    const toggleWalk = document.getElementById("toggle-walkaway-lock");
    toggleWalk?.addEventListener("change", () => {
      vibrate(20);
      sendWS("settings:walkaway_lock", { enabled: toggleWalk.checked });
    });

    // CCTV Intruder Guard
    const toggleGuard = document.getElementById("toggle-cctv-guard");
    toggleGuard?.addEventListener("change", () => {
      vibrate(25);
      sendWS("guard:toggle", { enabled: toggleGuard.checked });
    });

    // Intruder Alert Modal Actions
    document.getElementById("btn-intruder-lock")?.addEventListener("click", () => {
      vibrate(40);
      sendWS("system:action", { action: "lock" });
      document.getElementById("modal-intruder-alert")?.classList.add("hidden");
      showToast("🔒 PC Workstation Locked", "info");
    });

    document.getElementById("btn-intruder-alarm")?.addEventListener("click", () => {
      vibrate(30);
      sendWS("find_pc:start");
      document.getElementById("modal-intruder-alert")?.classList.add("hidden");
      showToast("🔊 PC Alarm Ringing!", "error");
    });

    document.getElementById("btn-intruder-dismiss")?.addEventListener("click", () => {
      document.getElementById("modal-intruder-alert")?.classList.add("hidden");
    });
  }

  function handleIntruderAlert(data) {
    vibrate([200, 100, 200, 100, 400]);
    const modal = document.getElementById("modal-intruder-alert");
    const img = document.getElementById("intruder-modal-img");
    const timeEl = document.getElementById("intruder-time-text");

    if (img && data.photo) img.src = data.photo;
    if (timeEl) timeEl.textContent = `Time: ${data.time || "Just now"} (${data.reason || "Physical movement detected"})`;
    if (modal) modal.classList.remove("hidden");

    updateIntruderPreview(data);
  }

  function updateIntruderPreview(data) {
    const box = document.getElementById("intruder-preview-box");
    const img = document.getElementById("intruder-preview-img");
    const timeEl = document.getElementById("intruder-preview-time");
    if (box && img && data.photo) {
      img.src = data.photo;
      if (timeEl) timeEl.textContent = data.time || "Just now";
      box.classList.remove("hidden");
    }
  }

  // --- 4. Live Hardware Monitor HUD Loop (2-sec auto refresh) ---
  let hudInterval = null;
  function setupLiveHUDLoop() {
    if (hudInterval) clearInterval(hudInterval);
    hudInterval = setInterval(() => {
      if (isConnected && (activeTab === "system" || activeTab === "trackpad")) {
        sendWS("system:stats");
      }
    }, 2000);
  }

})();
