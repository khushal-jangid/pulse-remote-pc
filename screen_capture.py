"""
Pulse Remote v2.0 - High-Speed Multi-Monitor Screen Capture & Coordinate Mapper
"""
import io
import base64
from typing import List, Dict, Any, Optional
from PIL import Image, ImageDraw
import config

class ScreenCapture:
    """Ultra-fast multi-monitor screen capture engine with dynamic coordinate mapping."""

    def __init__(self):
        self.selected_monitor_id = 1
        self.use_mss = True
        try:
            import mss
            self.sct = mss.mss()
        except Exception:
            self.use_mss = False
            self.sct = None

    def get_monitors_list(self) -> List[Dict[str, Any]]:
        """Detect and return all connected display monitors."""
        monitors = []
        if self.use_mss and self.sct:
            try:
                # mss.monitors[0] is the virtual canvas of all monitors combined.
                # mss.monitors[1..n] are the individual monitors.
                raw_monitors = self.sct.monitors[1:] if len(self.sct.monitors) > 1 else self.sct.monitors
                for idx, m in enumerate(raw_monitors, start=1):
                    is_primary = (m.get("left") == 0 and m.get("top") == 0) or idx == 1
                    monitors.append({
                        "id": idx,
                        "name": f"Monitor {idx}" + (" (Primary)" if is_primary else ""),
                        "width": m["width"],
                        "height": m["height"],
                        "left": m["left"],
                        "top": m["top"],
                        "is_primary": is_primary,
                        "is_active": idx == self.selected_monitor_id,
                    })
                return monitors
            except Exception:
                pass

        # Fallback for single monitor
        monitors.append({
            "id": 1,
            "name": "Primary Display",
            "width": 1920,
            "height": 1080,
            "left": 0,
            "top": 0,
            "is_primary": True,
            "is_active": True,
        })
        return monitors

    def get_screen_size(self) -> tuple[int, int]:
        """Get primary display dimensions (width, height)."""
        info = self.get_active_monitor_info()
        return info.get("width", 1920), info.get("height", 1080)

    def select_monitor(self, monitor_id: int) -> bool:
        """Select active monitor index for screen streaming."""
        monitors = self.get_monitors_list()
        for m in monitors:
            if m["id"] == monitor_id:
                self.selected_monitor_id = monitor_id
                return True
        return False

    def get_active_monitor_info(self) -> Dict[str, Any]:
        """Get geometry and details of currently selected monitor."""
        monitors = self.get_monitors_list()
        for m in monitors:
            if m["id"] == self.selected_monitor_id:
                return m
        return monitors[0] if monitors else {"width": 1920, "height": 1080, "left": 0, "top": 0}

    def map_relative_to_screen(self, rel_x: float, rel_y: float, monitor_id: Optional[int] = None) -> tuple[int, int]:
        """
        Map normalized [0..1] touch coordinates on selected monitor to absolute screen pixel coordinates.
        """
        m_id = monitor_id or self.selected_monitor_id
        monitors = self.get_monitors_list()
        target = next((m for m in monitors if m["id"] == m_id), monitors[0])

        abs_x = int(target["left"] + (rel_x * target["width"]))
        abs_y = int(target["top"] + (rel_y * target["height"]))
        return abs_x, abs_y

    def capture_frame_bytes(self, quality: int = config.SCREEN_JPEG_QUALITY, max_width: int = 1280, monitor_id: Optional[int] = None) -> bytes:
        """
        Capture selected monitor, downscale for low-latency streaming, and compress to JPEG.
        """
        target_id = monitor_id or self.selected_monitor_id
        img = None

        if self.use_mss and self.sct:
            try:
                raw_monitors = self.sct.monitors[1:] if len(self.sct.monitors) > 1 else self.sct.monitors
                idx = min(max(0, target_id - 1), len(raw_monitors) - 1)
                mon = raw_monitors[idx]
                raw = self.sct.grab(mon)
                img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
            except Exception:
                img = None

        if img is None:
            try:
                from PIL import ImageGrab
                img = ImageGrab.grab()
            except Exception:
                img = Image.new("RGB", (1280, 720), color=(15, 23, 42))
                draw = ImageDraw.Draw(img)
                draw.text((480, 340), f"Display {target_id} Locked or Idle", fill=(0, 242, 254))

        # Downscale for smooth mobile streaming
        if img.width > max_width:
            aspect = img.height / img.width
            new_height = int(max_width * aspect)
            img = img.resize((max_width, new_height), Image.Resampling.BILINEAR)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=False)
        return buf.getvalue()

    def capture_frame_base64(self, quality: int = config.SCREEN_JPEG_QUALITY, max_width: int = 1280, monitor_id: Optional[int] = None) -> str:
        """Capture frame and return base64 encoded data URL."""
        jpeg_bytes = self.capture_frame_bytes(quality=quality, max_width=max_width, monitor_id=monitor_id)
        encoded = base64.b64encode(jpeg_bytes).decode("ascii")
        return f"data:image/jpeg;base64,{encoded}"

# Global instance
screen = ScreenCapture()
