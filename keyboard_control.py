"""
Pulse Remote - Keyboard & System Shortcut Control
"""
import time
import sys
import pyautogui

# Disable pyautogui failsafe delay for snappy response
pyautogui.PAUSE = 0.01
pyautogui.FAILSAFE = False

KEY_MAP = {
    "enter": "enter",
    "return": "enter",
    "escape": "esc",
    "esc": "esc",
    "backspace": "backspace",
    "tab": "tab",
    "space": "space",
    " ": "space",
    "arrowup": "up",
    "up": "up",
    "arrowdown": "down",
    "down": "down",
    "arrowleft": "left",
    "left": "left",
    "arrowright": "right",
    "right": "right",
    "delete": "delete",
    "home": "home",
    "end": "end",
    "pageup": "pageup",
    "pagedown": "pagedown",
    "capslock": "capslock",
}

class KeyboardController:
    """Handles keyboard typing, special keys, and system hotkeys."""

    def type_text(self, text: str):
        """Type a full text string."""
        if not text:
            return
        try:
            pyautogui.write(text, interval=0.005)
        except Exception:
            # Fallback for unicode / non-ascii characters via clipboard
            import clipboard
            clipboard.clip.set_text(text)
            pyautogui.hotkey("ctrl", "v")

    def press_key(self, key_name: str):
        """Press a single key."""
        k = key_name.lower().strip()
        mapped = KEY_MAP.get(k, k)
        try:
            pyautogui.press(mapped)
        except Exception as e:
            print(f"[Keyboard] Key press error: {e}")

    def press_shortcut(self, shortcut: str):
        """
        Execute system shortcuts like:
        - 'ctrl+c', 'ctrl+v', 'ctrl+z', 'ctrl+a', 'ctrl+s', 'ctrl+w'
        - 'alt+tab', 'alt+f4'
        - 'win+d', 'win+e', 'win+l', 'win+r'
        - 'volume_up', 'volume_down', 'volume_mute', 'play_pause'
        """
        sc = shortcut.lower().strip()

        # Windows Media Keys
        if sc in ["play_pause", "play", "pause"]:
            pyautogui.press("playpause")
            return
        elif sc in ["volume_up", "vol_up"]:
            pyautogui.press("volumeup")
            return
        elif sc in ["volume_down", "vol_down"]:
            pyautogui.press("volumedown")
            return
        elif sc in ["volume_mute", "mute"]:
            pyautogui.press("volumemute")
            return
        elif sc in ["next_track", "next"]:
            pyautogui.press("nexttrack")
            return
        elif sc in ["prev_track", "prev"]:
            pyautogui.press("prevtrack")
            return

        # Handle Win key shortcuts specifically for Windows
        if sys.platform == "win32" and "win" in sc:
            parts = sc.split("+")
            other_key = [p for p in parts if p != "win"]
            if other_key:
                pyautogui.hotkey("win", other_key[0])
            else:
                pyautogui.press("win")
            return

        # General combination hotkeys
        parts = sc.split("+")
        try:
            pyautogui.hotkey(*parts)
        except Exception as e:
            print(f"[Keyboard] Shortcut error: {e}")

# Global instance
keyboard = KeyboardController()
