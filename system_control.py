"""
Pulse Remote v2.0 - System Metrics, Allowlisted App Launcher & Find My PC Engine
"""
import os
import sys
import time
import ctypes
import platform
import threading
import subprocess
import psutil
import config
from activity_log import audit_log

class SystemController:
    """Provides comprehensive system diagnostics, power management, app launching & Find My PC alarm."""

    def __init__(self):
        self._last_net_time = time.time()
        self._last_net_io = psutil.net_io_counters()
        self._upload_speed_kbps = 0.0
        self._download_speed_kbps = 0.0
        
        # Find My PC Alarm State
        self._find_pc_active = False
        self._find_pc_thread = None
        self._find_pc_window = None

        # Guard Mode State (CCTV Intruder Alert)
        self._guard_mode_active = False
        self._guard_thread = None
        self._last_intruder_info = None
        self._on_intruder_callback = None

        # Walk-Away Auto-Lock State
        self._walkaway_lock_enabled = False

        # Brightness Cache
        self._cached_brightness = 100
        self._brightness_initialized = False

    def get_system_stats(self) -> dict:
        """Fetch live CPU, RAM, Disk, Network I/O, Battery, and hardware metrics."""
        now = time.time()
        elapsed = max(0.1, now - self._last_net_time)
        cur_net_io = psutil.net_io_counters()

        # Calculate network throughput in KB/s
        sent_delta = cur_net_io.bytes_sent - self._last_net_io.bytes_sent
        recv_delta = cur_net_io.bytes_recv - self._last_net_io.bytes_recv
        self._upload_speed_kbps = round((sent_delta / elapsed) / 1024, 1)
        self._download_speed_kbps = round((recv_delta / elapsed) / 1024, 1)
        self._last_net_time = now
        self._last_net_io = cur_net_io

        cpu_usage = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        
        disk_path = "C:\\" if sys.platform == "win32" else "/"
        try:
            disk = psutil.disk_usage(disk_path)
            disk_info = {
                "total_gb": round(disk.total / (1024 ** 3), 1),
                "used_gb": round(disk.used / (1024 ** 3), 1),
                "free_gb": round(disk.free / (1024 ** 3), 1),
                "percent": disk.percent,
            }
        except Exception:
            disk_info = {"total_gb": 0, "used_gb": 0, "free_gb": 0, "percent": 0}

        battery_info = None
        try:
            bat = psutil.sensors_battery()
            if bat:
                battery_info = {
                    "percent": int(bat.percent),
                    "power_plugged": bool(bat.power_plugged),
                    "secsleft": bat.secsleft if bat.secsleft != psutil.POWER_TIME_UNLIMITED else None,
                }
        except Exception:
            pass

        # CPU info
        cpu_freq = psutil.cpu_freq()
        freq_mhz = round(cpu_freq.current, 0) if cpu_freq else 0

        # Initial brightness query
        if not self._brightness_initialized:
            self.get_brightness()
            self._brightness_initialized = True

        return {
            "device_name": config.DEVICE_NAME,
            "os": config.DEVICE_OS,
            "cpu_model": platform.processor() or "Multi-Core Processor",
            "cpu_percent": cpu_usage,
            "cpu_cores": psutil.cpu_count(logical=True),
            "cpu_freq_mhz": freq_mhz,
            "memory": {
                "total_gb": round(mem.total / (1024 ** 3), 1),
                "used_gb": round(mem.used / (1024 ** 3), 1),
                "free_gb": round(mem.available / (1024 ** 3), 1),
                "percent": mem.percent,
            },
            "disk": disk_info,
            "network": {
                "upload_kbps": self._upload_speed_kbps,
                "download_kbps": self._download_speed_kbps,
            },
            "battery": battery_info,
            "brightness": self._cached_brightness,
            "guard_mode_active": self._guard_mode_active,
            "walkaway_lock_enabled": self._walkaway_lock_enabled,
            "last_intruder": self._last_intruder_info,
            "uptime_seconds": int(time.time() - psutil.boot_time()),
            "find_pc_active": self._find_pc_active,
        }

    def launch_allowlisted_app(self, app_key: str, client_name: str = "Device") -> dict:
        """Launch an application from the predefined security allowlist."""
        app_key = app_key.lower().strip()
        app_entry = config.ALLOWLISTED_APPS.get(app_key)
        
        if not app_entry:
            return {"success": False, "message": f"App '{app_key}' is not in the security allowlist."}

        try:
            cmd = app_entry["command"]
            subprocess.Popen(cmd, shell=False)
            audit_log.log("APP_LAUNCH", f"Launched {app_entry['name']}", client_name)
            return {"success": True, "message": f"Launched {app_entry['name']}"}
        except Exception as e:
            return {"success": False, "message": f"Failed to launch {app_entry['name']}: {str(e)}"}

    def get_allowlisted_apps_list(self) -> list:
        """Get list of predefined quick actions for mobile UI."""
        return [
            {"key": k, "name": v["name"], "icon": v["icon"]}
            for k, v in config.ALLOWLISTED_APPS.items()
        ]

    def execute_power_action(self, action: str, client_name: str = "Device") -> dict:
        """Execute system power action with audit logging."""
        act = action.lower().strip()
        
        if act == "lock":
            if sys.platform == "win32":
                ctypes.windll.user32.LockWorkStation()
                audit_log.log("PC_LOCKED", "Emergency Lock triggered from mobile", client_name)
                return {"success": True, "message": "PC Locked Successfully"}
            return {"success": False, "message": "Lock only supported on Windows"}
            
        elif act == "sleep":
            if sys.platform == "win32":
                audit_log.log("PC_SLEEP", "Sleep mode triggered from mobile", client_name)
                subprocess.Popen(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
                return {"success": True, "message": "Entering Sleep Mode..."}
            return {"success": False, "message": "Sleep only supported on Windows"}
            
        elif act == "restart":
            if sys.platform == "win32":
                audit_log.log("PC_RESTART", "System restart requested", client_name)
                subprocess.Popen(["shutdown", "/r", "/t", "5"])
                return {"success": True, "message": "Restarting PC in 5 seconds..."}
            return {"success": False, "message": "Unsupported on this OS"}
            
        elif act == "shutdown":
            if sys.platform == "win32":
                audit_log.log("PC_SHUTDOWN", "System shutdown requested", client_name)
                subprocess.Popen(["shutdown", "/s", "/t", "5"])
                return {"success": True, "message": "Shutting down PC in 5 seconds..."}
            return {"success": False, "message": "Unsupported on this OS"}
            
        return {"success": False, "message": f"Unknown action: {action}"}

    # Find My PC Audio & Notification Engine
    def start_find_pc(self, client_name: str = "Device") -> dict:
        """Start playing an audible sound alert on PC and show visible screen banner."""
        if self._find_pc_active:
            return {"success": True, "message": "Find My PC is already ringing!"}

        self._find_pc_active = True
        audit_log.log("FIND_MY_PC", f"Find My PC sound triggered by {client_name}", client_name)

        def sound_loop():
            try:
                import winsound
                while self._find_pc_active:
                    winsound.Beep(1200, 250)
                    time.sleep(0.05)
                    winsound.Beep(1800, 350)
                    time.sleep(0.3)
            except Exception:
                pass

        self._find_pc_thread = threading.Thread(target=sound_loop, daemon=True)
        self._find_pc_thread.start()
        return {"success": True, "message": "🔊 PC sound is playing"}

    def is_find_pc_active(self) -> bool:
        """Check if Find My PC alarm is currently ringing."""
        return self._find_pc_active

    def stop_find_pc(self, client_name: str = "Device") -> dict:
        """Stop Find My PC alert sound."""
        self._find_pc_active = False
        audit_log.log("FIND_MY_PC_STOPPED", f"Find My PC sound stopped by {client_name}", client_name)
        return {"success": True, "message": "Find My PC sound stopped"}

    # --- Screen Brightness Controls ---
    def get_brightness(self) -> int:
        """Query current display brightness level (0-100%)."""
        if sys.platform != "win32":
            return 100
        try:
            res = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command", "(Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightness).CurrentBrightness"],
                text=True, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                timeout=2
            ).strip()
            if res:
                self._cached_brightness = int(res)
        except Exception:
            pass
        return self._cached_brightness

    def set_brightness(self, level: int) -> bool:
        """Set display brightness level (0-100%)."""
        if sys.platform != "win32":
            return False
        level = max(0, min(100, int(level)))
        self._cached_brightness = level
        try:
            cmd = f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, {level})"
            subprocess.Popen(
                ["powershell", "-NoProfile", "-Command", cmd],
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            return True
        except Exception:
            return False

    # --- Panic / Boss Key Mode (Anti-Spy) ---
    def trigger_panic_mode(self, client_name: str = "Device") -> dict:
        """1-Tap Boss Key: Minimizes all windows to desktop and mutes master audio."""
        try:
            import pyautogui
            # Minimize all windows
            pyautogui.hotkey('win', 'd')
            # Mute master volume
            pyautogui.press('volumemute')
            audit_log.log("PANIC_MODE", "🚨 Boss Key triggered: Desktop revealed & audio muted", client_name)
            return {"success": True, "message": "🚨 Boss Mode Engaged: Screen hidden & audio muted!"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # --- CCTV Stealth PC Guard Engine ---
    def start_guard_mode(self, on_intruder_callback=None, client_name: str = "Device") -> dict:
        """Activate CCTV Stealth PC Guard mode."""
        if self._guard_mode_active:
            return {"success": True, "active": True, "message": "Guard Mode is already ACTIVE"}

        self._guard_mode_active = True
        self._on_intruder_callback = on_intruder_callback
        audit_log.log("GUARD_MODE_ON", "CCTV Stealth PC Guard activated", client_name)

        def guard_worker():
            try:
                import pyautogui
                from webcam_capture import webcam
                last_pos = pyautogui.position()
                last_alert_time = 0

                while self._guard_mode_active:
                    time.sleep(0.4)
                    cur_pos = pyautogui.position()
                    dx = abs(cur_pos.x - last_pos.x)
                    dy = abs(cur_pos.y - last_pos.y)
                    now = time.time()

                    # Trigger alert on significant physical mouse movement
                    if (dx > 25 or dy > 25) and (now - last_alert_time > 8):
                        last_alert_time = now
                        last_pos = cur_pos
                        photo_b64 = webcam.capture_frame_base64(quality=70)
                        timestr = time.strftime("%Y-%m-%d %H:%M:%S")
                        self._last_intruder_info = {
                            "time": timestr,
                            "photo": photo_b64,
                            "reason": f"PC Mouse moved ({dx}px, {dy}px)"
                        }
                        audit_log.log("INTRUDER_DETECTED", "Stealth camera captured intruder on PC movement!", "Guard Engine")
                        if self._on_intruder_callback:
                            self._on_intruder_callback(self._last_intruder_info)
                    else:
                        last_pos = cur_pos
            except Exception as e:
                print(f"[Guard] Worker error: {e}")

        self._guard_thread = threading.Thread(target=guard_worker, daemon=True)
        self._guard_thread.start()
        return {"success": True, "active": True, "message": "🛡️ CCTV PC Guard is now ACTIVE!"}

    def stop_guard_mode(self, client_name: str = "Device") -> dict:
        """Deactivate CCTV Stealth PC Guard mode."""
        self._guard_mode_active = False
        audit_log.log("GUARD_MODE_OFF", "CCTV Stealth PC Guard deactivated", client_name)
        return {"success": True, "active": False, "message": "🛡️ CCTV PC Guard deactivated"}

    def is_guard_mode_active(self) -> bool:
        return self._guard_mode_active

    def get_last_intruder(self) -> dict:
        return self._last_intruder_info or {}

    # --- Walk-Away Proximity Auto-Lock ---
    def set_walkaway_lock(self, enabled: bool, client_name: str = "Device") -> dict:
        self._walkaway_lock_enabled = enabled
        status_txt = "ENABLED" if enabled else "DISABLED"
        audit_log.log("WALKAWAY_LOCK", f"Walk-Away Auto-Lock set to {status_txt}", client_name)
        return {"success": True, "enabled": self._walkaway_lock_enabled}

    def is_walkaway_lock_enabled(self) -> bool:
        return self._walkaway_lock_enabled

# Global instance
system = SystemController()
