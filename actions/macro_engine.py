"""
AEGIS Macro Engine
Records and replays user keyboard and mouse interactions using pynput and pyautogui.
Provides accurate relative timing, structured JSON storage, and safe execution.
"""

import os
import time
import json
import re
import threading
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union

# Try importing configuration defaults
try:
    from aegis.config import DATA_DIR
    DEFAULT_STORAGE_DIR = DATA_DIR / "macros"
except ImportError:
    DEFAULT_STORAGE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "macros"

# Safe imports for automation libraries
try:
    import pyautogui
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0.0
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    pyautogui = None
    PYAUTOGUI_AVAILABLE = False

try:
    from pynput import mouse, keyboard
    PYNPUT_AVAILABLE = True
except ImportError:
    mouse = None
    keyboard = None
    PYNPUT_AVAILABLE = False


class MacroEngine:
    """
    Automates recording and playback of desktop keyboard and mouse actions.
    Uses pynput for background event capture and pyautogui for precision playback.
    """

    # Mapping of pynput key identifier strings to pyautogui key names
    KEY_MAP = {
        "alt_l": "altleft",
        "alt_r": "altright",
        "alt_gr": "altright",
        "alt": "alt",
        "ctrl_l": "ctrlleft",
        "ctrl_r": "ctrlright",
        "ctrl": "ctrl",
        "control": "ctrl",
        "shift_l": "shiftleft",
        "shift_r": "shiftright",
        "shift": "shift",
        "cmd": "win",
        "cmd_l": "winleft",
        "cmd_r": "winright",
        "super": "win",
        "windows": "win",
        "win_l": "winleft",
        "win_r": "winright",
        "caps_lock": "capslock",
        "page_down": "pagedown",
        "page_up": "pageup",
        "print_screen": "printscreen",
        "scroll_lock": "scrolllock",
        "num_lock": "numlock",
        "media_play_pause": "playpause",
        "media_volume_mute": "volumemute",
        "media_volume_up": "volumeup",
        "media_volume_down": "volumedown",
        "media_next": "nexttrack",
        "media_previous": "prevtrack",
        "media_stop": "stop",
        "escape": "esc",
        "return": "enter",
    }

    def __init__(self, storage_dir: Optional[Union[str, Path]] = None):
        """
        Initializes MacroEngine with a storage directory for macro JSON files.
        Defaults to data/macros/ relative to project root.
        """
        if storage_dir is not None:
            self.storage_dir = Path(storage_dir).resolve()
        else:
            self.storage_dir = DEFAULT_STORAGE_DIR.resolve()

        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"[MacroEngine Error] Failed to create storage directory '{self.storage_dir}': {e}")

        self._is_recording = False
        self._is_playing = False
        self._recording_name = ""
        self._events: List[Dict[str, Any]] = []
        self._start_time = 0.0
        self._last_move_time = 0.0
        self._lock = threading.Lock()
        self._mouse_listener: Optional[Any] = None
        self._keyboard_listener: Optional[Any] = None

    @property
    def is_recording(self) -> bool:
        """Returns whether a recording session is currently active."""
        return self._is_recording

    @property
    def is_playing(self) -> bool:
        """Returns whether a playback session is currently active."""
        return self._is_playing

    def _serialize_key(self, key: Any) -> str:
        """Converts a pynput Key or KeyCode object into a clean string identifier."""
        try:
            if hasattr(key, "char") and key.char is not None:
                return key.char
            if hasattr(key, "name") and key.name is not None:
                return key.name
            k_str = str(key)
            if k_str.startswith("Key."):
                return k_str[4:]
            if k_str.startswith("'<") and k_str.endswith(">'"):
                return k_str[2:-2]
            if k_str.startswith("'") and k_str.endswith("'"):
                return k_str[1:-1]
            return k_str
        except Exception as e:
            print(f"[MacroEngine Error] Key serialization failed for '{key}': {e}")
            return str(key)

    def _normalize_key(self, raw_key: str) -> Optional[str]:
        """Normalizes recorded key string for safe execution with pyautogui."""
        if not raw_key:
            return None

        clean_key = raw_key.replace("Key.", "").strip()
        lower_key = clean_key.lower()

        if lower_key in self.KEY_MAP:
            return self.KEY_MAP[lower_key]

        if pyautogui and lower_key in pyautogui.KEYBOARD_KEYS:
            return lower_key

        if pyautogui and clean_key in pyautogui.KEYBOARD_KEYS:
            return clean_key

        if len(clean_key) == 1:
            return clean_key

        return lower_key

    def _record_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Records an event with relative timestamp from recording start."""
        if not self._is_recording:
            return
        timestamp = round(time.time() - self._start_time, 4)
        event = {
            "type": event_type,
            "data": data,
            "timestamp": timestamp
        }
        with self._lock:
            if self._is_recording:
                self._events.append(event)

    def _on_mouse_move(self, x: int, y: int) -> None:
        """Callback for mouse move events with rate limiting."""
        now = time.time()
        # Limit move recording to ~50 Hz to prevent ballooning file size while preserving motion smoothness
        if now - self._last_move_time < 0.02:
            return
        self._last_move_time = now
        self._record_event("move", {"x": int(x), "y": int(y)})

    def _on_mouse_click(self, x: int, y: int, button: Any, pressed: bool) -> None:
        """Callback for mouse click press and release events."""
        button_name = getattr(button, "name", str(button).replace("Button.", "")).lower()
        self._record_event("click", {
            "x": int(x),
            "y": int(y),
            "button": button_name,
            "pressed": bool(pressed),
            "action": "press" if pressed else "release"
        })

    def _on_key_press(self, key: Any) -> None:
        """Callback for keyboard press events."""
        key_str = self._serialize_key(key)
        self._record_event("key", {
            "key": key_str,
            "action": "press"
        })

    def _on_key_release(self, key: Any) -> None:
        """Callback for keyboard release events."""
        key_str = self._serialize_key(key)
        self._record_event("key", {
            "key": key_str,
            "action": "release"
        })

    def start_recording(self, name: str) -> Tuple[bool, str]:
        """
        Starts capturing keyboard and mouse events in background threads using pynput.
        Records events as {type: 'key'|'click'|'move', data: ..., timestamp: float}.
        """
        if not PYNPUT_AVAILABLE:
            msg = "pynput is not installed or available. Cannot record macros."
            print(f"[MacroEngine Error] {msg}")
            return False, msg

        clean_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', name.strip())
        if not clean_name:
            msg = "Macro name cannot be empty."
            print(f"[MacroEngine Error] {msg}")
            return False, msg

        with self._lock:
            if self._is_recording:
                msg = f"Already recording macro '{self._recording_name}'. Stop it before starting a new one."
                print(f"[MacroEngine Error] {msg}")
                return False, msg

            self._is_recording = True
            self._recording_name = clean_name
            self._events = []
            self._start_time = time.time()
            self._last_move_time = 0.0

        try:
            self._mouse_listener = mouse.Listener(
                on_move=self._on_mouse_move,
                on_click=self._on_mouse_click
            )
            self._keyboard_listener = keyboard.Listener(
                on_press=self._on_key_press,
                on_release=self._on_key_release
            )

            self._mouse_listener.daemon = True
            self._keyboard_listener.daemon = True
            self._mouse_listener.start()
            self._keyboard_listener.start()

            return True, f"Started recording macro '{clean_name}'."
        except Exception as e:
            self._is_recording = False
            msg = f"Failed to start input listeners: {e}"
            print(f"[MacroEngine Error] {msg}")
            return False, msg

    def stop_recording(self) -> Optional[Dict[str, Any]]:
        """
        Stops active event listeners, saves events to JSON file <name>.json in storage_dir,
        and returns the macro dict: {name, events: [...], recorded_at, duration_seconds}.
        """
        with self._lock:
            if not self._is_recording:
                print("[MacroEngine Error] stop_recording called but no active recording session found.")
                return None

            self._is_recording = False
            duration = time.time() - self._start_time
            macro_name = self._recording_name

        # Terminate listeners
        try:
            if self._mouse_listener is not None:
                self._mouse_listener.stop()
                self._mouse_listener = None
        except Exception as e:
            print(f"[MacroEngine Error] Error stopping mouse listener: {e}")

        try:
            if self._keyboard_listener is not None:
                self._keyboard_listener.stop()
                self._keyboard_listener = None
        except Exception as e:
            print(f"[MacroEngine Error] Error stopping keyboard listener: {e}")

        with self._lock:
            events = list(self._events)
            self._events = []
            self._recording_name = ""

        macro_data = {
            "name": macro_name,
            "events": events,
            "recorded_at": datetime.datetime.now().isoformat(),
            "duration_seconds": round(duration, 3)
        }

        # Save to storage
        file_path = self.storage_dir / f"{macro_name}.json"
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(macro_data, f, indent=2)
            return macro_data
        except Exception as e:
            print(f"[MacroEngine Error] Failed to write macro JSON to '{file_path}': {e}")
            return macro_data

    def _replay_key(self, raw_key: str, action: str = "press") -> None:
        """Replays a single keyboard event safely with pyautogui."""
        if not pyautogui:
            return

        normalized = self._normalize_key(raw_key)
        if not normalized:
            return

        try:
            if action == "press":
                pyautogui.keyDown(normalized)
            elif action == "release":
                pyautogui.keyUp(normalized)
            else:
                pyautogui.press(normalized)
        except Exception as e:
            # Fallback attempts for special keys or direct press
            try:
                if action == "press":
                    pyautogui.press(normalized)
            except Exception:
                pass
            print(f"[MacroEngine Error] Failed to replay key '{raw_key}' ({action}): {e}")

    def play_macro(self, name: str, speed_multiplier: float = 1.0) -> Tuple[bool, str]:
        """
        Loads JSON macro file and replays events using pyautogui with accurate relative timing.
        """
        if not PYAUTOGUI_AVAILABLE:
            msg = "pyautogui is not installed or available. Cannot play macros."
            print(f"[MacroEngine Error] {msg}")
            return False, msg

        clean_name = name.strip()
        if clean_name.endswith(".json"):
            clean_name = clean_name[:-5]

        file_path = self.storage_dir / f"{clean_name}.json"
        if not file_path.exists():
            msg = f"Macro '{clean_name}' not found at '{file_path}'."
            print(f"[MacroEngine Error] {msg}")
            return False, msg

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                macro_data = json.load(f)
        except Exception as e:
            msg = f"Failed to load macro '{clean_name}': {e}"
            print(f"[MacroEngine Error] {msg}")
            return False, msg

        events = macro_data.get("events", [])
        if not events:
            return True, f"Macro '{clean_name}' has 0 recorded events."

        # Sort chronologically by timestamp
        sorted_events = sorted(events, key=lambda ev: ev.get("timestamp", 0.0))

        with self._lock:
            self._is_playing = True

        try:
            pyautogui.FAILSAFE = False
            pyautogui.PAUSE = 0.0

            start_time = time.time()
            for ev in sorted_events:
                with self._lock:
                    if not self._is_playing:
                        return False, "Macro playback was interrupted or stopped."

                target_ts = ev.get("timestamp", 0.0)
                if speed_multiplier > 0:
                    adjusted_target = target_ts / speed_multiplier
                else:
                    adjusted_target = target_ts

                current_elapsed = time.time() - start_time
                delay = adjusted_target - current_elapsed
                if delay > 0.001:
                    time.sleep(delay)

                ev_type = ev.get("type")
                ev_data = ev.get("data", {})

                if ev_type == "move":
                    x = ev_data.get("x")
                    y = ev_data.get("y")
                    if x is not None and y is not None:
                        pyautogui.moveTo(x, y)

                elif ev_type == "click":
                    x = ev_data.get("x")
                    y = ev_data.get("y")
                    btn = ev_data.get("button", "left").lower()
                    pressed = ev_data.get("pressed")
                    if pressed is None:
                        action = ev_data.get("action", "press")
                        pressed = (action == "press")

                    if btn not in ["left", "right", "middle", "primary", "secondary"]:
                        btn = "left"

                    if pressed:
                        if x is not None and y is not None:
                            pyautogui.mouseDown(x=x, y=y, button=btn)
                        else:
                            pyautogui.mouseDown(button=btn)
                    else:
                        if x is not None and y is not None:
                            pyautogui.mouseUp(x=x, y=y, button=btn)
                        else:
                            pyautogui.mouseUp(button=btn)

                elif ev_type == "key":
                    raw_key = ev_data.get("key")
                    action = ev_data.get("action", "press")
                    if raw_key:
                        self._replay_key(raw_key, action)

            duration = round(time.time() - start_time, 2)
            return True, f"Successfully replayed macro '{clean_name}' ({len(sorted_events)} events in {duration}s)."
        except Exception as e:
            msg = f"Playback execution failed: {e}"
            print(f"[MacroEngine Error] {msg}")
            return False, msg
        finally:
            with self._lock:
                self._is_playing = False

    def stop_playback(self) -> None:
        """Aborts any currently running macro playback."""
        with self._lock:
            self._is_playing = False

    def list_macros(self) -> List[str]:
        """
        Returns a sorted list of available macro names (without .json extension) from storage_dir.
        """
        try:
            if not self.storage_dir.exists():
                return []
            macro_files = self.storage_dir.glob("*.json")
            return sorted([f.stem for f in macro_files if f.is_file()])
        except Exception as e:
            print(f"[MacroEngine Error] list_macros failed: {e}")
            return []

    def get_macro(self, name: str) -> Optional[Dict[str, Any]]:
        """Loads and returns the macro dictionary for the given name, or None if not found."""
        clean_name = name.strip()
        if clean_name.endswith(".json"):
            clean_name = clean_name[:-5]
        file_path = self.storage_dir / f"{clean_name}.json"
        if not file_path.exists():
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[MacroEngine Error] Failed to read macro '{clean_name}': {e}")
            return None

    def delete_macro(self, name: str) -> Tuple[bool, str]:
        """
        Deletes a macro JSON file from storage_dir.
        """
        clean_name = name.strip()
        if clean_name.endswith(".json"):
            clean_name = clean_name[:-5]

        file_path = self.storage_dir / f"{clean_name}.json"
        try:
            if not file_path.exists():
                msg = f"Macro '{clean_name}' not found."
                return False, msg

            file_path.unlink()
            return True, f"Macro '{clean_name}' deleted successfully."
        except Exception as e:
            msg = f"Failed to delete macro '{clean_name}': {e}"
            print(f"[MacroEngine Error] {msg}")
            return False, msg


if __name__ == "__main__":
    print("=== AEGIS MacroEngine Test ===")
    engine = MacroEngine()

    # 1. List available macros
    macros = engine.list_macros()
    print(f"Storage Directory: {engine.storage_dir}")
    print(f"Available Macros ({len(macros)}): {macros}")

    # 2. Test saving, reading, and deleting a mock macro
    test_macro_name = "__test_mock_macro__"
    test_file = engine.storage_dir / f"{test_macro_name}.json"
    mock_macro = {
        "name": test_macro_name,
        "events": [
            {"type": "move", "data": {"x": 100, "y": 100}, "timestamp": 0.01},
            {"type": "click", "data": {"x": 100, "y": 100, "button": "left", "pressed": True, "action": "press"}, "timestamp": 0.05},
            {"type": "click", "data": {"x": 100, "y": 100, "button": "left", "pressed": False, "action": "release"}, "timestamp": 0.10},
            {"type": "key", "data": {"key": "a", "action": "press"}, "timestamp": 0.15},
            {"type": "key", "data": {"key": "a", "action": "release"}, "timestamp": 0.20}
        ],
        "recorded_at": datetime.datetime.now().isoformat(),
        "duration_seconds": 0.25
    }

    try:
        with open(test_file, "w", encoding="utf-8") as f:
            json.dump(mock_macro, f, indent=2)
        print(f"Created test mock macro: {test_macro_name}")

        updated_macros = engine.list_macros()
        print(f"Updated Macro List: {updated_macros}")
        assert test_macro_name in updated_macros, "Test macro should be in list"

        loaded = engine.get_macro(test_macro_name)
        print(f"Loaded macro details: name='{loaded.get('name') if loaded else None}', events_count={len(loaded.get('events', [])) if loaded else 0}")

        deleted, del_msg = engine.delete_macro(test_macro_name)
        print(f"Cleanup: {del_msg} (success={deleted})")
        assert test_macro_name not in engine.list_macros(), "Test macro should be deleted"

        print("=== MacroEngine Self-Test Passed Successfully ===")
    except Exception as err:
        print(f"[MacroEngine Error] Self-test failed: {err}")
        if test_file.exists():
            test_file.unlink()
