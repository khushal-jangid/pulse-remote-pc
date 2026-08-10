# Python Worker Engine for PulseRemote PC
# Win32 GDI, Motion Security, Speedometer, Windows Switcher, RAM Cleaner & Brightness Remote

import sys
import json
import os
import ctypes
import io
import base64
import time
import re
import subprocess
import threading
import pyautogui
import psutil
import cv2
from PIL import Image

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.0001

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Global streaming flags & threads
screen_streaming = False
webcam_streaming = False
stats_streaming = False
motion_guard_active = False

screen_thread = None
webcam_thread = None
stats_thread = None
motion_thread = None
webcam_cap = None
stream_lock = threading.Lock()

# Clipboard History Vault Storage
clipboard_history = []
last_clip_text = ""

# Previous Network I/O counters
last_net_bytes_sent = 0
last_net_bytes_recv = 0
last_net_time = time.time()
last_power_plugged = True

# Win32 Setup
user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

def win32_screenshot():
    width = user32.GetSystemMetrics(0)
    height = user32.GetSystemMetrics(1)

    hdc_screen = user32.GetDC(0)
    hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
    hbmp = gdi32.CreateCompatibleBitmap(hdc_screen, width, height)
    gdi32.SelectObject(hdc_mem, hbmp)

    gdi32.BitBlt(hdc_mem, 0, 0, width, height, hdc_screen, 0, 0, 0x00CC0020)

    bmp_header = ctypes.create_string_buffer(40)
    ctypes.c_uint32.from_buffer(bmp_header, 0).value = 40
    ctypes.c_int32.from_buffer(bmp_header, 4).value = width
    ctypes.c_int32.from_buffer(bmp_header, 8).value = -height
    ctypes.c_uint16.from_buffer(bmp_header, 12).value = 1
    ctypes.c_uint16.from_buffer(bmp_header, 14).value = 32
    ctypes.c_uint32.from_buffer(bmp_header, 16).value = 0

    bmp_size = width * height * 4
    buffer = ctypes.create_string_buffer(bmp_size)
    gdi32.GetDIBits(hdc_mem, hbmp, 0, height, buffer, bmp_header, 0)

    gdi32.DeleteObject(hbmp)
    gdi32.DeleteDC(hdc_mem)
    user32.ReleaseDC(0, hdc_screen)

    img = Image.frombytes('RGBA', (width, height), buffer.raw, 'raw', 'BGRA')
    return img.convert('RGB')

VK_MAP = {
    "volume_up": 0xAF, "volume_down": 0xAE, "mute": 0xAD, "play_pause": 0xB3,
    "next": 0xB0, "prev": 0xB1, "enter": 0x0D, "backspace": 0x08, "tab": 0x09,
    "esc": 0x1B, "space": 0x20, "left": 0x25, "up": 0x26, "right": 0x27,
    "down": 0x28, "win": 0x5B, "ctrl": 0x11, "alt": 0x12, "shift": 0x10
}

def send_win32_vk(vk_code):
    try:
        ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
        ctypes.windll.user32.keybd_event(vk_code, 0, 2, 0)
    except Exception as e:
        sys.stderr.write(f"VK Error: {e}\n")

# Feature 39: Get Open Active Desktop Windows
def get_open_windows():
    windows = []
    seen = set()
    try:
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                name = proc.info['name']
                if not name or name.lower() in ['svchost.exe', 'system', 'idle', 'explorer.exe', 'py-worker.exe']:
                    continue
                app_title = name.replace('.exe', '').capitalize()
                if app_title not in seen:
                    seen.add(app_title)
                    windows.append({'pid': proc.info['pid'], 'name': name, 'title': app_title})
            except Exception:
                pass
    except Exception as e:
        sys.stderr.write(f"Enum Windows Error: {e}\n")
    return windows[:12]

# Feature 39: Focus Selected Window
def focus_window(app_name):
    try:
        proc_name = app_name.replace('.exe', '')
        cmd = ["powershell", "-Command", f"$w = New-Object -ComObject wscript.shell; $w.AppActivate('{proc_name}')"]
        subprocess.run(cmd, capture_output=True, text=True)
    except Exception as e:
        sys.stderr.write(f"Focus Window Error: {e}\n")

# Feature 44: Set PC Screen Brightness (0-100%)
def set_screen_brightness(val):
    try:
        val = max(0, min(100, int(val)))
        cmd = ["powershell", "-Command", f"(Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, {val})"]
        subprocess.run(cmd, capture_output=True, text=True)
    except Exception as e:
        sys.stderr.write(f"Brightness Error: {e}\n")

# Feature 48: 1-Tap RAM Working Set Trim
def trim_system_ram():
    freed = 0
    try:
        for proc in psutil.process_iter(['pid']):
            try:
                handle = ctypes.windll.kernel32.OpenProcess(0x1F0FFF, False, proc.info['pid'])
                if handle:
                    ctypes.windll.psapi.EmptyWorkingSet(handle)
                    ctypes.windll.kernel32.CloseHandle(handle)
                    freed += 1
            except Exception:
                pass
    except Exception as e:
        sys.stderr.write(f"RAM Trim Error: {e}\n")
    return freed

# Feature 48: 1-Tap Temp Files & DNS Cleanup
def clean_temp_files():
    try:
        os.system("del /q /f /s %temp%\\* >nul 2>&1")
        os.system("ipconfig /flushdns >nul 2>&1")
    except Exception as e:
        sys.stderr.write(f"Temp Clean Error: {e}\n")

def get_wifi_signal():
    try:
        out = subprocess.check_output('netsh wlan show interfaces', shell=True, text=True, errors='ignore')
        match = re.search(r'Signal\s*:\s*(\d+)%', out)
        if match:
            return int(match.group(1))
    except Exception:
        pass
    return 100

def get_hardware_stats():
    global last_net_bytes_sent, last_net_bytes_recv, last_net_time, last_power_plugged, last_clip_text
    try:
        cpu = psutil.cpu_percent(interval=None)
        vmem = psutil.virtual_memory()
        ram_percent = vmem.percent
        ram_used_gb = round(vmem.used / (1024 ** 3), 1)
        ram_total_gb = round(vmem.total / (1024 ** 3), 1)

        batt = psutil.sensors_battery()
        batt_percent = batt.percent if batt else 100
        batt_plugged = batt.power_plugged if batt else True

        if last_power_plugged and not batt_plugged:
            alert_obj = {
                "type": "sys_alert",
                "alert_type": "power_unplugged",
                "title": "🔌 Power Charger Unplugged!",
                "message": "PC laptop charger was disconnected or power went out."
            }
            with stream_lock:
                print(json.dumps(alert_obj), flush=True)

        last_power_plugged = batt_plugged

        if ram_percent > 92 or cpu > 92:
            alert_obj = {
                "type": "sys_alert",
                "alert_type": "high_stress",
                "title": "⚠️ System High Stress Warning!",
                "message": f"PC Stress Critical: CPU {cpu}% | RAM {ram_percent}%"
            }
            with stream_lock:
                print(json.dumps(alert_obj), flush=True)

        now = time.time()
        time_delta = max(0.1, now - last_net_time)
        net_io = psutil.net_io_counters()

        down_speed_kb = round(max(0, (net_io.bytes_recv - last_net_bytes_recv) / 1024 / time_delta), 1)
        up_speed_kb = round(max(0, (net_io.bytes_sent - last_net_bytes_sent) / 1024 / time_delta), 1)

        last_net_bytes_recv = net_io.bytes_recv
        last_net_bytes_sent = net_io.bytes_sent
        last_net_time = now

        wifi = get_wifi_signal()

        # Check Clipboard History (Feature 46)
        try:
            import pyperclip
            clip_curr = pyperclip.paste()
            if clip_curr and clip_curr != last_clip_text and len(clip_curr.strip()) > 0:
                last_clip_text = clip_curr
                if clip_curr not in clipboard_history:
                    clipboard_history.insert(0, clip_curr)
                    if len(clipboard_history) > 10:
                        clipboard_history.pop()
        except Exception:
            pass

        return {
            "type": "sys_stats",
            "cpu": cpu,
            "ram": ram_percent,
            "ram_used": ram_used_gb,
            "ram_total": ram_total_gb,
            "battery": batt_percent,
            "plugged": batt_plugged,
            "wifi": wifi,
            "down_speed_kb": down_speed_kb,
            "up_speed_kb": up_speed_kb,
            "clipboard_history": clipboard_history[:8]
        }
    except Exception as e:
        sys.stderr.write(f"Stats Error: {e}\n")
        return None

# REAL-TIME HARDWARE STATS LOOP
def stats_stream_loop():
    global stats_streaming, last_net_bytes_sent, last_net_bytes_recv
    psutil.cpu_percent(interval=None)
    net_init = psutil.net_io_counters()
    last_net_bytes_sent = net_init.bytes_sent
    last_net_bytes_recv = net_init.bytes_recv

    while stats_streaming:
        try:
            stats = get_hardware_stats()
            if stats:
                with stream_lock:
                    print(json.dumps(stats), flush=True)
            time.sleep(1.2)
        except Exception as e:
            sys.stderr.write(f"Stats Stream Error: {e}\n")
            time.sleep(2)

# MOTION SECURITY GUARD THREAD
def motion_guard_loop():
    global motion_guard_active
    cap = None
    try:
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(0)

        if not cap.isOpened():
            sys.stderr.write("Motion Guard Camera failed to open\n")
            motion_guard_active = False
            return

        ret, prev_frame = cap.read()
        if not ret or prev_frame is None:
            motion_guard_active = False
            return

        prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
        last_alert_time = 0

        while motion_guard_active:
            ret, frame = cap.read()
            if not ret or frame is None:
                time.sleep(0.1)
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            diff = cv2.absdiff(prev_gray, gray)
            _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
            motion_pixels = cv2.countNonZero(thresh)

            prev_gray = gray

            now = time.time()
            if motion_pixels > 6000 and (now - last_alert_time) > 8:
                last_alert_time = now

                _, jpeg_buf = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 65])
                b64_snapshot = base64.b64encode(jpeg_buf).decode('utf-8')

                alert_obj = {
                    "type": "intruder_alert",
                    "title": "🚨 INTRUDER MOTION DETECTED!",
                    "message": "Webcam detected movement in front of your PC!",
                    "timestamp": time.strftime("%H:%M:%S"),
                    "image": b64_snapshot
                }
                with stream_lock:
                    print(json.dumps(alert_obj), flush=True)

            time.sleep(0.15)
    except Exception as e:
        sys.stderr.write(f"Motion Guard Error: {e}\n")
    finally:
        if cap is not None:
            try:
                cap.release()
                cv2.destroyAllWindows()
            except Exception:
                pass
        sys.stderr.write("MOTION GUARD CAMERA RELEASED\n")

# REAL-TIME SCREEN MIRROR THREAD
def screen_stream_loop():
    global screen_streaming
    while screen_streaming:
        try:
            img = win32_screenshot()
            target_w = 800
            target_h = int(img.height * (target_w / img.width))
            resized = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
            
            buf = io.BytesIO()
            resized.save(buf, format="JPEG", quality=50)
            b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")
            
            out_obj = {
                "type": "screen_frame",
                "data": b64_str,
                "width": img.width,
                "height": img.height
            }
            with stream_lock:
                print(json.dumps(out_obj), flush=True)
            time.sleep(0.06)
        except Exception as e:
            sys.stderr.write(f"Screen Stream Error: {e}\n")
            time.sleep(0.2)

# REAL-TIME WEBCAM STREAM THREAD
def webcam_stream_loop():
    global webcam_streaming, webcam_cap
    try:
        webcam_cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not webcam_cap.isOpened():
            webcam_cap = cv2.VideoCapture(0)
            
        if not webcam_cap.isOpened():
            sys.stderr.write("Webcam failed to open\n")
            webcam_streaming = False
            return

        while webcam_streaming:
            ret, frame = webcam_cap.read()
            if not ret or frame is None:
                time.sleep(0.05)
                continue

            h, w, _ = frame.shape
            target_w = 640
            target_h = int(h * (target_w / w))
            resized = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_AREA)

            _, jpeg_buf = cv2.imencode('.jpg', resized, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
            b64_str = base64.b64encode(jpeg_buf).decode('utf-8')

            out_obj = {
                "type": "webcam_frame",
                "data": b64_str
            }
            with stream_lock:
                print(json.dumps(out_obj), flush=True)
            time.sleep(0.06)
    except Exception as e:
        sys.stderr.write(f"Webcam Error: {e}\n")
    finally:
        if webcam_cap is not None:
            try:
                webcam_cap.release()
                cv2.destroyAllWindows()
            except Exception:
                pass
            webcam_cap = None
        sys.stderr.write("WEBCAM HARDWARE RELEASED & LED OFF\n")
        sys.stderr.flush()

print("READY", flush=True)

while True:
    try:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue

        cmd = json.loads(line)
        action = cmd.get("action")

        # FEATURE 39: GET OPEN WINDOWS & FOCUS
        if action == "get_open_windows":
            wins = get_open_windows()
            out_obj = {"type": "open_windows", "windows": wins}
            with stream_lock:
                print(json.dumps(out_obj), flush=True)

        elif action == "focus_window":
            app_name = cmd.get("app", "")
            if app_name:
                focus_window(app_name)

        # FEATURE 44: BRIGHTNESS CONTROL
        elif action == "set_brightness":
            val = cmd.get("value", 80)
            set_screen_brightness(val)

        # FEATURE 48: QUICK MAINTENANCE (RAM TRIM & TEMP CLEAN)
        elif action == "trim_ram":
            freed = trim_system_ram()
            out_obj = {"type": "sys_alert", "alert_type": "info", "title": "🧠 RAM Trimmed!", "message": f"Freed working set for {freed} processes."}
            with stream_lock:
                print(json.dumps(out_obj), flush=True)

        elif action == "clean_temp":
            clean_temp_files()
            out_obj = {"type": "sys_alert", "alert_type": "info", "title": "🧹 Temp Files Cleaned!", "message": "Cleared %temp% files and flushed DNS cache."}
            with stream_lock:
                print(json.dumps(out_obj), flush=True)

        # MOTION GUARD CONTROLS
        elif action == "start_motion_guard":
            if not motion_guard_active:
                motion_guard_active = True
                motion_thread = threading.Thread(target=motion_guard_loop, daemon=True)
                motion_thread.start()

        elif action == "stop_motion_guard":
            motion_guard_active = False

        # HARDWARE STATS CONTROLS
        elif action == "start_stats_stream":
            if not stats_streaming:
                stats_streaming = True
                stats_thread = threading.Thread(target=stats_stream_loop, daemon=True)
                stats_thread.start()

        elif action == "stop_stats_stream":
            stats_streaming = False

        elif action == "get_stats":
            stats = get_hardware_stats()
            if stats:
                with stream_lock:
                    print(json.dumps(stats), flush=True)

        # SCREEN MIRROR CONTROLS
        elif action == "start_screen_stream":
            if not screen_streaming:
                screen_streaming = True
                screen_thread = threading.Thread(target=screen_stream_loop, daemon=True)
                screen_thread.start()

        elif action == "stop_screen_stream":
            screen_streaming = False

        # WEBCAM CONTROLS
        elif action == "start_webcam_stream":
            if not webcam_streaming:
                webcam_streaming = True
                webcam_thread = threading.Thread(target=webcam_stream_loop, daemon=True)
                webcam_thread.start()

        elif action == "stop_webcam_stream":
            webcam_streaming = False

        # CLIPBOARD SYNC
        elif action == "set_clipboard":
            text = cmd.get("text", "")
            if text:
                try:
                    import pyperclip
                    pyperclip.copy(text)
                except Exception as e:
                    sys.stderr.write(f"Clipboard Error: {e}\n")

        # MOUSE ACTIONS
        elif action == "move_rel":
            dx = int(cmd.get("dx", 0))
            dy = int(cmd.get("dy", 0))
            try:
                pyautogui.moveRel(dx, dy)
            except Exception:
                ctypes.windll.user32.mouse_event(0x0001, dx, dy, 0, 0)

        elif action == "move_abs":
            x = int(cmd.get("x", 0))
            y = int(cmd.get("y", 0))
            try:
                pyautogui.moveTo(x, y)
            except Exception:
                ctypes.windll.user32.SetCursorPos(x, y)

        elif action == "click":
            button = cmd.get("button", "left")
            try:
                pyautogui.click(button=button)
            except Exception:
                if button == "right":
                    ctypes.windll.user32.mouse_event(0x0008, 0, 0, 0, 0)
                    ctypes.windll.user32.mouse_event(0x0010, 0, 0, 0, 0)
                else:
                    ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)
                    ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)

        elif action == "double_click":
            try:
                pyautogui.doubleClick()
            except Exception:
                ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)
                ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)

        elif action == "mouse_down":
            button = cmd.get("button", "left")
            try:
                pyautogui.mouseDown(button=button)
            except Exception:
                if button == "right":
                    ctypes.windll.user32.mouse_event(0x0008, 0, 0, 0, 0)
                else:
                    ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)

        elif action == "mouse_up":
            button = cmd.get("button", "left")
            try:
                pyautogui.mouseUp(button=button)
            except Exception:
                if button == "right":
                    ctypes.windll.user32.mouse_event(0x0010, 0, 0, 0, 0)
                else:
                    ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)

        elif action == "scroll":
            dy = int(cmd.get("dy", 0))
            try:
                pyautogui.scroll(dy * 25)
            except Exception:
                ctypes.windll.user32.mouse_event(0x0800, 0, 0, dy * 120, 0)

        elif action == "hscroll":
            dx = int(cmd.get("dx", 0))
            try:
                pyautogui.hscroll(dx * 25)
            except Exception:
                ctypes.windll.user32.mouse_event(0x01000, 0, 0, dx * 120, 0)

        elif action == "type":
            text = cmd.get("text", "")
            if text:
                try:
                    pyautogui.write(text)
                except Exception:
                    pass

        elif action == "key":
            k = cmd.get("key", "")
            if k in VK_MAP:
                send_win32_vk(VK_MAP[k])
            else:
                try:
                    pyautogui.press(k)
                except Exception:
                    pass

        elif action == "hotkey":
            combo = cmd.get("combo", "")
            if combo:
                keys = combo.split("+")
                try:
                    pyautogui.hotkey(*keys)
                except Exception:
                    pass

        elif action == "media":
            sub = cmd.get("type", "")
            if sub in VK_MAP:
                send_win32_vk(VK_MAP[sub])

        elif action == "system":
            sub = cmd.get("type", "")
            if sub == "lock":
                ctypes.windll.user32.LockWorkStation()
            elif sub == "sleep":
                os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
            elif sub == "shutdown":
                os.system("shutdown /s /t 0")
            elif sub == "restart":
                os.system("shutdown /r /t 0")

        elif action == "launch":
            app = cmd.get("app", "")
            app_map = {
                "browser": "start https://google.com",
                "youtube": "start https://youtube.com",
                "notepad": "start notepad.exe",
                "calc": "start calc.exe",
                "explorer": "start explorer.exe",
                "taskmgr": "start taskmgr.exe"
            }
            if app in app_map:
                os.system(app_map[app])

        elif action == "screenshot":
            try:
                img = win32_screenshot()
                target_w = 800
                target_h = int(img.height * (target_w / img.width))
                resized = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
                
                buf = io.BytesIO()
                resized.save(buf, format="JPEG", quality=50)
                b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")
                
                out_obj = {
                    "type": "screen_frame",
                    "data": b64_str,
                    "width": img.width,
                    "height": img.height
                }
                with stream_lock:
                    print(json.dumps(out_obj), flush=True)
            except Exception as e:
                sys.stderr.write(f"Screenshot Error: {e}\n")

    except Exception as e:
        sys.stderr.write(f"ERR: {e}\n")
        sys.stderr.flush()

webcam_streaming = False
screen_streaming = False
stats_streaming = False
motion_guard_active = False
if webcam_cap is not None:
    try:
        webcam_cap.release()
        cv2.destroyAllWindows()
    except Exception:
        pass
