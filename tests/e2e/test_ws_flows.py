"""End-to-end flows over the real WebSocket gateway, exactly as the React app uses it."""
import asyncio

import pytest

from backend.main import manager
from backend.services.scheduler import reminder_scheduler

pytestmark = pytest.mark.e2e


def collect_until(ws, wanted_type, limit=15):
    seen = []
    for _ in range(limit):
        msg = ws.receive_json()
        seen.append(msg)
        if msg["type"] == wanted_type:
            return msg, seen
    raise AssertionError(f"never received {wanted_type}; saw {[m['type'] for m in seen]}")


def test_connect_sends_init_snapshot(client):
    with client.websocket_connect("/ws") as ws:
        init = ws.receive_json()
        assert init["type"] == "init" and "clock" in init and "suggestions" in init


def test_text_command_runs_think_execute_speak_cycle(client):
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "message", "text": "what is the date today"})
        resp, seen = collect_until(ws, "agent_response")
        states = [m["state"] for m in seen if m["type"] == "state_change"]
        assert states[:2] == ["THINKING", "SPEAKING"]
        assert resp["tool"] == "get_system_date" and resp["route"] == "router"


def test_live_vision_returns_smoothed_tracked_targets(client, jpeg_b64):
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "camera_state", "active": True})
        collect_until(ws, "camera_status")
        for _ in range(3):
            ws.send_json({"type": "camera_frame_sync", "frame_base64": jpeg_b64, "live_detect": True})
            det, _ = collect_until(ws, "live_detections")
        assert det["engine"] in {"yolov5m", "yolox", "heuristic"}
        assert det["frame_w"] == 640 and det["frame_h"] == 480
        for box in det["boxes"]:
            assert 0 <= box["rel_x"] <= 1 and "id" in box and "stable" in box


def test_camera_off_resets_tracking(client, jpeg_b64):
    from backend.services.tracker import detection_tracker
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "camera_frame_sync", "frame_base64": jpeg_b64})
        collect_until(ws, "live_detections")
        ws.send_json({"type": "camera_state", "active": False})
        status, _ = collect_until(ws, "camera_status")
        assert status["active"] is False and detection_tracker.tracks == []


def test_where_is_my_phone_after_scan_uses_visual_memory(client):
    from backend.services.visual_memory import visual_memory_engine
    visual_memory_engine.store_observation("phone", "on the desk", room="workspace",
                                           spatial_relationship="on the desk on the left")
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "message", "text": "where is my phone"})
        resp, _ = collect_until(ws, "agent_response")
        assert resp["tool"] == "query_visual_memory" and "phone" in resp["response"]


def test_due_reminder_is_pushed_to_client(client, monkeypatch):
    import datetime
    from backend.database import SessionLocal
    from backend.models import Reminder
    from backend import main as main_module

    async def no_tts(_text):  # keep the test offline
        return None
    monkeypatch.setattr(main_module.tts_service, "generate_speech_audio_base64", no_tts)

    db = SessionLocal()
    db.add(Reminder(text="drink water", reminder_time=datetime.datetime.now() - datetime.timedelta(seconds=1)))
    db.commit()
    db.close()

    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        # the real APScheduler job runs every 3 s; invoke the same check directly for determinism
        client.portal.call(reminder_scheduler.check_due_reminders)
        alert, _ = collect_until(ws, "reminder_alert")
        assert alert["text"] == "drink water"


def test_barge_in_cancels_speech(client):
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "barge_in"})
        assert ws.receive_json() == {"type": "state_change", "state": "LISTENING"}


def test_ping_pong_keeps_clock_in_sync(client):
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "ping"})
        pong = ws.receive_json()
        assert pong["type"] == "pong" and "clock" in pong
