"""
Pulse Remote v2.0 - High-Performance Async Network Server & Secure Protocol Engine
"""
import os
import sys
import json
import asyncio
from pathlib import Path
from aiohttp import web, WSMsgType

import config
from authentication import auth_manager
from mouse_control import mouse
from keyboard_control import keyboard
from screen_capture import screen
from webcam_capture import webcam
from clipboard import clip
from file_manager import files
from system_control import system
from activity_log import audit_log

if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    bundled_static = Path(sys._MEIPASS) / "static"
    if bundled_static.exists():
        STATIC_DIR = bundled_static
    else:
        STATIC_DIR = Path(sys.executable).resolve().parent / "static"
else:
    STATIC_DIR = Path(__file__).resolve().parent / "static"

class NetworkServer:
    """Asynchronous HTTP and WebSocket server for Pulse Remote v2.0."""

    def __init__(self, on_device_connected=None, on_device_disconnected=None):
        self.app = web.Application(client_max_size=config.MAX_UPLOAD_SIZE)
        self.runner = None
        self.site = None
        self.active_ws_connections = set()
        self.on_device_connected = on_device_connected
        self.on_device_disconnected = on_device_disconnected
        self._setup_routes()

    def _setup_routes(self):
        # API Routes
        self.app.router.add_post("/api/pair", self.handle_pair)
        self.app.router.add_get("/api/status", self.handle_status)
        self.app.router.add_get("/api/files/download", self.handle_file_download)
        self.app.router.add_post("/api/files/upload", self.handle_file_upload)
        self.app.router.add_get("/api/security/logs", self.handle_security_logs)
        self.app.router.add_get("/ws", self.handle_websocket)

        # Static Web Client Routes
        self.app.router.add_get("/", self.handle_index)
        self.app.router.add_static("/static", path=str(STATIC_DIR), name="static")

    async def handle_index(self, request):
        """Serve the mobile remote web application."""
        index_file = STATIC_DIR / "index.html"
        if index_file.exists():
            return web.FileResponse(index_file, headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"})
        return web.Response(text="Pulse Remote Web Client starting...", content_type="text/html")

    async def handle_status(self, request):
        """Check server availability and basic device info."""
        return web.json_response({
            "status": "online",
            "version": "2.0.0",
            "device_id": config.DEVICE_ID,
            "device_name": config.DEVICE_NAME,
            "os": config.DEVICE_OS,
            "active_sessions": len(auth_manager.get_active_sessions()),
        })

    async def handle_security_logs(self, request):
        """Fetch security activity audit logs."""
        token = request.headers.get("X-Session-Token") or request.query.get("token")
        if not auth_manager.validate_session(token):
            return web.json_response({"error": "Unauthorized"}, status=401)
        return web.json_response({"logs": audit_log.get_logs()})

    async def handle_pair(self, request):
        """Validate temporary QR pairing token and return session token."""
        try:
            data = await request.json()
            token = data.get("pairing_token")
            client_device = data.get("device_id", "phone")
            client_name = data.get("name", "Smartphone")

            if not token:
                return web.json_response({"error": "Missing pairing_token"}, status=400)

            client_info = {
                "device_id": client_device,
                "name": client_name,
                "ip": request.remote,
            }

            session_token = auth_manager.validate_and_consume_pairing_token(token, client_info)
            if not session_token:
                return web.json_response({"error": "Invalid or expired pairing token"}, status=401)

            if self.on_device_connected:
                self.on_device_connected(client_info)

            return web.json_response({
                "success": True,
                "session_token": session_token,
                "device_id": config.DEVICE_ID,
                "device_name": config.DEVICE_NAME,
                "permissions": auth_manager.validate_session(session_token).get("permissions", {}),
            })
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def handle_file_download(self, request):
        """Stream a requested file from PC to mobile with permission check."""
        session_token = request.query.get("token")
        if not auth_manager.check_permission(session_token, "files"):
            return web.Response(text="Unauthorized / Permission Denied", status=403)

        file_path = request.query.get("path")
        if not file_path or not os.path.exists(file_path) or not os.path.isfile(file_path):
            return web.Response(text="File not found", status=404)

        session_info = auth_manager.validate_session(session_token)
        client_name = session_info.get("client_name", "Device") if session_info else "Device"
        audit_log.log("FILE_DOWNLOAD", f"Downloaded '{os.path.basename(file_path)}'", client_name)

        return web.FileResponse(file_path)

    async def handle_file_upload(self, request):
        """Handle file upload from mobile to PC with permission check."""
        session_token = request.headers.get("X-Session-Token") or request.query.get("token")
        if not auth_manager.check_permission(session_token, "files"):
            return web.json_response({"error": "Permission Denied: File transfers disabled for this device."}, status=403)

        reader = await request.multipart()
        field = await reader.next()
        dest_dir = request.query.get("dir") or str(Path.home() / "Downloads")

        if field and field.filename:
            file_data = await field.read()
            res = files.save_uploaded_file(dest_dir, field.filename, file_data)
            
            session_info = auth_manager.validate_session(session_token)
            client_name = session_info.get("client_name", "Device") if session_info else "Device"
            audit_log.log("FILE_UPLOAD", f"Uploaded '{res['filename']}' ({res['size']} bytes)", client_name)
            return web.json_response(res)

        return web.json_response({"error": "No file uploaded"}, status=400)

    async def handle_websocket(self, request):
        """Real-time bidirectional WebSocket handler with granular per-device permission enforcement."""
        ws = web.WebSocketResponse(heartbeat=10.0)
        await ws.prepare(request)
        self.active_ws_connections.add(ws)

        authenticated = False
        session_token = None
        client_name = "Phone"
        client_id = None

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        event = data.get("event")
                        payload = data.get("data", {})

                        # 1. Authentication Handshake
                        if event == "auth":
                            session_token = payload.get("session_token")
                            session_info = auth_manager.validate_session(session_token)
                            if session_info:
                                authenticated = True
                                client_name = session_info.get("client_name", "Phone")
                                client_id = session_info.get("client_id")
                                audit_log.log("DEVICE_CONNECTED", f"Device '{client_name}' connected", client_name, request.remote)
                                
                                await ws.send_json({
                                    "event": "auth_success",
                                    "data": {
                                        "device_name": config.DEVICE_NAME,
                                        "device_id": config.DEVICE_ID,
                                        "permissions": session_info.get("permissions", {}),
                                    }
                                })
                                if self.on_device_connected:
                                    self.on_device_connected(client_name)
                            else:
                                await ws.send_json({"event": "auth_error", "data": {"error": "Invalid session token"}})
                                await ws.close()
                                break
                            continue

                        # Ensure client is authenticated before processing any command
                        if not authenticated:
                            await ws.send_json({"event": "auth_required", "data": {}})
                            continue

                        # Helper for permission checks
                        def require_permission(perm_name: str) -> bool:
                            if not auth_manager.check_permission(session_token, perm_name):
                                asyncio.create_task(ws.send_json({
                                    "event": "permission_denied",
                                    "data": {"permission": perm_name, "message": f"Action '{perm_name}' is disabled for this device."}
                                }))
                                return False
                            return True

                        # 2. Mouse Controls
                        if event == "mouse:move":
                            if require_permission("mouse"):
                                mouse.move(payload.get("dx", 0), payload.get("dy", 0), payload.get("sensitivity", 1.0))

                        elif event == "mouse:click":
                            if require_permission("mouse"):
                                mouse.click(payload.get("button", "left"), payload.get("double", False))

                        elif event == "mouse:down":
                            if require_permission("mouse"):
                                mouse.mouse_down(payload.get("button", "left"))

                        elif event == "mouse:up":
                            if require_permission("mouse"):
                                mouse.mouse_up(payload.get("button", "left"))

                        elif event == "mouse:scroll":
                            if require_permission("mouse"):
                                mouse.scroll(payload.get("dy", 0), payload.get("dx", 0))

                        elif event == "mouse:click_rel":
                            # Multi-monitor touch-to-click mapping
                            if require_permission("mouse"):
                                rel_x = payload.get("rel_x", 0)
                                rel_y = payload.get("rel_y", 0)
                                mon_id = payload.get("monitor_id")
                                abs_x, abs_y = screen.map_relative_to_screen(rel_x, rel_y, mon_id)
                                mouse.set_position(abs_x, abs_y)
                                mouse.click(payload.get("button", "left"))

                        # 3. Keyboard Controls
                        elif event == "keyboard:type":
                            if require_permission("keyboard"):
                                keyboard.type_text(payload.get("text", ""))

                        elif event == "keyboard:key":
                            if require_permission("keyboard"):
                                keyboard.press_key(payload.get("key", ""))

                        elif event == "keyboard:shortcut":
                            if require_permission("keyboard"):
                                keyboard.press_shortcut(payload.get("shortcut", ""))

                        # 4. Multi-Monitor & Screen Mirroring
                        elif event == "monitors:list":
                            mon_list = screen.get_monitors_list()
                            await ws.send_json({"event": "monitors:list_data", "data": {"monitors": mon_list}})

                        elif event == "monitors:select":
                            mon_id = payload.get("monitor_id", 1)
                            screen.select_monitor(mon_id)
                            audit_log.log("MONITOR_SWITCHED", f"Switched to Monitor {mon_id}", client_name)
                            await ws.send_json({"event": "monitors:selected", "data": {"monitor_id": mon_id}})

                        elif event == "screen:frame":
                            if require_permission("screen"):
                                quality = payload.get("quality", config.SCREEN_JPEG_QUALITY)
                                max_w = payload.get("maxWidth", 1280)
                                mon_id = payload.get("monitor_id")
                                frame_b64 = screen.capture_frame_base64(quality=quality, max_width=max_w, monitor_id=mon_id)
                                await ws.send_json({"event": "screen:frame_data", "data": {"frame": frame_b64}})

                        # 5. PC Webcam Live Video
                        elif event == "webcam:list":
                            if require_permission("webcam"):
                                cam_list = webcam.get_available_cameras()
                                await ws.send_json({"event": "webcam:list_data", "data": {"cameras": cam_list}})

                        elif event == "webcam:frame":
                            if require_permission("webcam"):
                                cam_id = payload.get("camera_id", 0)
                                quality = payload.get("quality", config.WEBCAM_JPEG_QUALITY)
                                frame_b64 = webcam.capture_frame_base64(cam_id=cam_id, quality=quality)
                                await ws.send_json({"event": "webcam:frame_data", "data": {"frame": frame_b64}})

                        elif event == "webcam:stop":
                            webcam.release()

                        # 6. Media Controls
                        elif event == "media:command":
                            if require_permission("media"):
                                cmd = payload.get("command", "")
                                keyboard.press_shortcut(cmd)

                        # 7. Quick Actions & App Launcher (Allowlisted)
                        elif event == "app:list":
                            apps = system.get_allowlisted_apps_list()
                            await ws.send_json({"event": "app:list_data", "data": {"apps": apps}})

                        elif event == "app:launch":
                            if require_permission("app_launcher"):
                                app_key = payload.get("app_key", "")
                                res = system.launch_allowlisted_app(app_key, client_name)
                                await ws.send_json({"event": "app:launch_result", "data": res})

                        # 8. Find My PC Alarm
                        elif event == "find_pc:start":
                            res = system.start_find_pc(client_name)
                            await ws.send_json({"event": "find_pc:status", "data": res})

                        elif event == "find_pc:stop":
                            res = system.stop_find_pc(client_name)
                            await ws.send_json({"event": "find_pc:status", "data": res})

                        # 9. Clipboard Sync & History
                        elif event == "clipboard:get":
                            if require_permission("clipboard"):
                                text = clip.get_text()
                                history = clip.get_history()
                                await ws.send_json({"event": "clipboard:data", "data": {"text": text, "history": history}})

                        elif event == "clipboard:set":
                            if require_permission("clipboard"):
                                text = payload.get("text", "")
                                clip.set_text(text, client_name)
                                await ws.send_json({"event": "clipboard:updated", "data": {"success": True}})

                        elif event == "clipboard:clear":
                            if require_permission("clipboard"):
                                clip.clear_clipboard()
                                audit_log.log("CLIPBOARD_CLEARED", "PC clipboard cleared", client_name)
                                await ws.send_json({"event": "clipboard:cleared", "data": {"success": True}})

                        # 10. System Stats & Power Actions
                        elif event == "system:stats":
                            stats = system.get_system_stats()
                            await ws.send_json({"event": "system:stats_data", "data": stats})

                        elif event == "system:action":
                            act = payload.get("action", "")
                            # Map action to permission
                            perm_map = {
                                "lock": "power_lock",
                                "sleep": "power_lock",
                                "restart": "power_restart",
                                "shutdown": "power_shutdown",
                            }
                            perm = perm_map.get(act, "power_lock")
                            if require_permission(perm):
                                res = system.execute_power_action(act, client_name)
                                await ws.send_json({"event": "system:action_result", "data": res})

                        # 11. File Manager
                        elif event == "files:list":
                            if require_permission("files"):
                                target_p = payload.get("path")
                                dir_res = files.list_directory(target_p)
                                await ws.send_json({"event": "files:list_data", "data": dir_res})

                        # 12. Paired Devices Management & Permissions
                        elif event == "devices:list":
                            devs = auth_manager.get_paired_devices()
                            await ws.send_json({"event": "devices:list_data", "data": {"devices": devs}})

                        elif event == "devices:update_perms":
                            target_id = payload.get("device_id")
                            new_perms = payload.get("permissions", {})
                            if target_id and new_perms:
                                success = auth_manager.update_device_permissions(target_id, new_perms)
                                await ws.send_json({"event": "devices:perms_updated", "data": {"success": success}})

                        elif event == "devices:revoke":
                            target_id = payload.get("device_id")
                            if target_id:
                                success = auth_manager.revoke_device(target_id)
                                await ws.send_json({"event": "devices:revoked", "data": {"success": success, "device_id": target_id}})

                        elif event == "devices:revoke_all":
                            count = auth_manager.revoke_all_sessions()
                            await ws.send_json({"event": "devices:all_revoked", "data": {"count": count}})

                        # 13. Security Activity Logs
                        elif event == "security:logs":
                            logs = audit_log.get_logs()
                            await ws.send_json({"event": "security:logs_data", "data": {"logs": logs}})

                        # 14. Custom Remotes Persistence
                        elif event == "custom_remotes:get":
                            remotes_data = []
                            if config.CUSTOM_REMOTES_FILE.exists():
                                try:
                                    remotes_data = json.loads(config.CUSTOM_REMOTES_FILE.read_text(encoding="utf-8"))
                                except Exception:
                                    pass
                            await ws.send_json({"event": "custom_remotes:data", "data": {"remotes": remotes_data}})

                        elif event == "custom_remotes:save":
                            remotes = payload.get("remotes", [])
                            try:
                                config.CUSTOM_REMOTES_FILE.write_text(json.dumps(remotes, indent=2), encoding="utf-8")
                                audit_log.log("CUSTOM_REMOTES_SAVED", f"Saved {len(remotes)} custom remote profile(s)", client_name)
                                await ws.send_json({"event": "custom_remotes:saved", "data": {"success": True}})
                            except Exception as e:
                                await ws.send_json({"event": "custom_remotes:saved", "data": {"success": False, "error": str(e)}})

                        # 15. Panic / Boss Key Mode (1-Tap Anti-Spy)
                        elif event == "system:panic":
                            res = system.trigger_panic_mode(client_name)
                            await ws.send_json({"event": "system:panic_result", "data": res})

                        # 16. Screen Brightness Slider
                        elif event == "brightness:set":
                            level = payload.get("level", 100)
                            success = system.set_brightness(level)
                            await ws.send_json({"event": "brightness:changed", "data": {"level": level, "success": success}})

                        # 17. CCTV Stealth PC Guard Engine
                        elif event == "guard:toggle":
                            enabled = payload.get("enabled", False)
                            if enabled:
                                def notify_intruder(intruder_data):
                                    for conn in list(self.active_ws_connections):
                                        try:
                                            asyncio.run_coroutine_threadsafe(
                                                conn.send_json({"event": "guard:intruder_alert", "data": intruder_data}),
                                                self.loop
                                            )
                                        except Exception as err:
                                            print(f"[Guard] Alert broadcast error: {err}")

                                res = system.start_guard_mode(notify_intruder, client_name)
                            else:
                                res = system.stop_guard_mode(client_name)
                            await ws.send_json({"event": "guard:status", "data": res})

                        # 18. Walk-Away Proximity Auto-Lock Setting
                        elif event == "settings:walkaway_lock":
                            enabled = payload.get("enabled", False)
                            res = system.set_walkaway_lock(enabled, client_name)
                            await ws.send_json({"event": "settings:walkaway_status", "data": res})

                    except json.JSONDecodeError:
                        pass
        finally:
            self.active_ws_connections.discard(ws)
            webcam.release()
            if authenticated:
                audit_log.log("DEVICE_DISCONNECTED", f"Device '{client_name}' disconnected", client_name)
            if self.on_device_disconnected and not self.active_ws_connections:
                self.on_device_disconnected()
            # Walk-Away Proximity Auto-Lock: lock workstation if all devices disconnect
            if not self.active_ws_connections and system.is_walkaway_lock_enabled():
                print("[Security] 🚶 Walk-Away Auto-Lock triggered: Device disconnected!")
                system.execute_power_action("lock", "WalkAway_AutoLock")

        return ws

    async def start(self, host: str = config.HOST, port: int = config.PORT):
        """Start aiohttp web server."""
        self.loop = asyncio.get_running_loop()
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, host, port)
        await self.site.start()
        print(f"[*] Pulse Remote v2.0 Server running on http://{host}:{port}")

    async def stop(self):
        """Stop server gracefully."""
        webcam.release()
        if self.runner:
            await self.runner.cleanup()
