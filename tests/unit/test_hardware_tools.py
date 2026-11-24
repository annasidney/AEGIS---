import pytest

from backend.tools import hardware_tools as hw

pytestmark = pytest.mark.unit


def test_brightness_up_down_clamped():
    assert hw.parse_brightness_request("up", None, current=90) == 100
    assert hw.parse_brightness_request("down", None, current=10) == 0


def test_brightness_set_and_clamp():
    assert hw.parse_brightness_request("set", 40) == 40
    assert hw.parse_brightness_request("set", 250) == 100
    assert hw.parse_brightness_request("set", None) is None


def test_hardware_tools_degrade_gracefully_off_windows(monkeypatch):
    monkeypatch.setattr(hw, "_is_windows", lambda: False)
    assert hw.set_brightness("up")["status"] == "unsupported"
    assert hw.lock_screen()["status"] == "unsupported"


def test_battery_status_shape():
    r = hw.get_battery_status()
    assert r["status"] in {"ok", "no_battery"} and "message" in r
