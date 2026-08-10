const { spawn } = require('child_process');
const path = require('path');
const EventEmitter = require('events');

class PyBridge extends EventEmitter {
  constructor() {
    super();
    this.py = null;
    this.isReady = false;
    this.queue = [];
    this.init();
  }

  init() {
    const scriptPath = path.join(__dirname, 'py-worker.py');
    this.py = spawn('python', [scriptPath], {
      stdio: ['pipe', 'pipe', 'pipe'],
      windowsHide: true
    });

    let buffer = '';

    this.py.stdout.on('data', (chunk) => {
      const text = chunk.toString('utf8');
      buffer += text;
      
      let lines = buffer.split('\n');
      buffer = lines.pop();

      for (let line of lines) {
        line = line.trim();
        if (!line) continue;

        if (line === 'READY') {
          console.log('\x1b[32m[PyBridge]\x1b[0m Python Automation Engine initialized & READY.');
          this.isReady = true;
          this.flushQueue();
          continue;
        }

        try {
          const data = JSON.parse(line);
          if (data.type === 'screen_frame') {
            this.emit('screen_frame', data);
          } else if (data.type === 'webcam_frame') {
            this.emit('webcam_frame', data);
          } else if (data.type === 'sys_stats') {
            this.emit('sys_stats', data);
          } else if (data.type === 'intruder_alert') {
            this.emit('intruder_alert', data);
          } else if (data.type === 'sys_alert') {
            this.emit('sys_alert', data);
          } else if (data.type === 'open_windows') {
            this.emit('open_windows', data);
          }
        } catch (e) {
          // non-json line
        }
      }
    });

    this.py.stderr.on('data', (data) => {
      const errStr = data.toString('utf8');
      if (errStr.includes('WEBCAM HARDWARE RELEASED')) {
        console.log('\x1b[33m[PyBridge]\x1b[0m 📷 Webcam Hardware Released & LED OFF');
      } else {
        console.error('\x1b[31m[PyBridge Error]:\x1b[0m', errStr);
      }
    });

    this.py.on('close', (code) => {
      console.log(`[PyBridge] Python process closed with code ${code}. Respawning in 1s...`);
      this.isReady = false;
      setTimeout(() => this.init(), 1000);
    });
  }

  send(cmdObj) {
    const jsonStr = JSON.stringify(cmdObj) + '\n';
    if (this.isReady && this.py && !this.py.killed) {
      this.py.stdin.write(jsonStr);
    } else {
      this.queue.push(jsonStr);
    }
  }

  flushQueue() {
    while (this.queue.length > 0 && this.isReady) {
      const item = this.queue.shift();
      this.py.stdin.write(item);
    }
  }

  close() {
    if (this.py) {
      this.py.kill();
    }
  }
}

module.exports = new PyBridge();
