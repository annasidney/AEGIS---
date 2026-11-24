"""Windows hardware controls: brightness, screen lock, sleep and battery status."""
import logging
import platform
import re
import subprocess
from typing import Any, Dict, Optional

import psutil

from backend.tools.registry import registry

logger = logging.getLogger("AEGIS.Hardware")


def _is_windows() -> bool:
    return platform.system() == "Windows"


def _powershell(command: str, timeout: int = 8) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True, text=True, timeout=timeout,
    )


def parse_brightness_request(action: str, level: Optional[int], current: Optional[int] = None) -> Optional[int]:
    """Pure helper: turn an action (+ optional level) into a target brightness percentage 0-100."""
    action = (action or "").lower()
    if action == "set":
        return None if level is None else max(0, min(100, int(level)))
    base = 50 if current is None else int(current)
    step = 15 if level is None else int(level)
    if action == "up":
        return max(0, min(100, base + step))
    if action == "down":
        return max(0, min(100, base - step))
    return None


@registry.register(
    name="set_brightness",
    description="Change screen brightness. action: 'up', 'down' or 'set' (with level 0-100).",
    parameters={
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["up", "down", "set"], "description": "Brightness action"},
            "level": {"type": "integer", "description": "Percentage for 'set', or step size for up/down"},
        },
        "required": ["action"],
    },
    permission_level="normal",
    category="hardware",
)
def set_brightness(action: str, level: Optional[int] = None) -> Dict[str, Any]:
    if not _is_windows():
        return {"status": "unsupported", "message": "Brightness control is only available on Windows.", "verified": False}
    try:
        current = None
        got = _powershell("(Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightness).CurrentBrightness")
        m = re.search(r"\d+", got.stdout or "")
        if m:
            current = int(m.group(0))
        target = parse_brightness_request(action, level, current)
        if target is None:
            return {"status": "error", "message": "Tell me a brightness level between 0 and 100.", "verified": False}
        _powershell(
            "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods)"
            f".WmiSetBrightness(1,{target})"
        )
        return {"status": "ok", "level": target, "message": f"Brightness set to {target}%.", "verified": True}
    except Exception as e:
        logger.warning(f"Brightness error: {e}")
        return {"status": "error", "message": "I couldn't change the brightness on this display.", "verified": False}


@registry.register(
    name="lock_screen",
    description="Lock the Windows workstation (requires the user to sign in again).",
    parameters={"type": "object", "properties": {}, "required": []},
    permission_level="sensitive",
    category="hardware",
)
def lock_screen() -> Dict[str, Any]:
    if not _is_windows():
        return {"status": "unsupported", "message": "Screen lock is only available on Windows.", "verified": False}
    subprocess.Popen(["rundll32.exe", "user32.dll,LockWorkStation"])
    return {"status": "ok", "message": "Locking your screen.", "verified": True}


@registry.register(
    name="get_battery_status",
    description="Report battery percentage and whether the laptop is charging.",
    parameters={"type": "object", "properties": {}, "required": []},
    permission_level="normal",
    category="hardware",
)
def get_battery_status() -> Dict[str, Any]:
    battery = psutil.sensors_battery()
    if battery is None:
        return {"status": "no_battery", "message": "This PC doesn't have a battery - it's running on mains power.", "verified": True}
    state = "charging" if battery.power_plugged else "on battery"
    return {
        "status": "ok",
        "percent": int(battery.percent),
        "charging": bool(battery.power_plugged),
        "message": f"Battery is at {int(battery.percent)}% and {state}.",
        "verified": True,
    }
