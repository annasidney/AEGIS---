import pytest

from backend import auth

pytestmark = pytest.mark.integration


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_status_reports_engines(client):
    data = client.get("/api/status").json()
    assert data["vision_engine"] in {"yolov5m", "yolox", "heuristic"}
    assert "clock" in data and "date" in data
    assert data["google_auth_enabled"] is True


def test_chat_uses_deterministic_router_and_reports_latency(client):
    data = client.post("/api/chat", json={"text": "what time is it"}).json()
    assert data["route"] == "router" and data["tool"] == "get_system_time"
    assert data["latency_ms"] < 50
    assert client.get("/api/status").json()["router_latency_ms"] is not None


def test_chat_math(client):
    data = client.post("/api/chat", json={"text": "15% of 200"}).json()
    assert "30" in data["response"]


def test_reminder_crud(client):
    created = client.post("/api/reminders", json={"text": "submit assignment", "time_str": "in 2 hours"}).json()
    assert created["status"] == "created"
    listed = client.get("/api/reminders").json()
    assert listed["reminders"][0]["text"] == "submit assignment"
    rid = created["id"]
    assert client.delete(f"/api/reminders/{rid}").json()["status"] == "deleted"
    assert client.get("/api/reminders").json()["status"] == "empty"


def test_routines_endpoint_returns_suggestions_after_repeated_use(client):
    from backend.services.routine_learner import routine_learner
    for _ in range(3):
        routine_learner.log_action("website_open", "YouTube")
    data = client.get("/api/routines").json()
    assert data["routines"] and data["suggestions"]
    assert client.delete("/api/routines").json()["cleared_count"] >= 1


def test_personal_memory_crud(client):
    client.post("/api/memories", json={"key": "favourite_drink", "value": "filter coffee"})
    mems = client.get("/api/memories").json()["memories"]
    assert mems[0]["key"] == "favourite_drink"
    assert client.delete(f"/api/memories/{mems[0]['id']}").json()["success"] is True


def test_visual_memory_endpoints(client):
    from backend.services.visual_memory import visual_memory_engine
    visual_memory_engine.store_observation("phone", "on the desk")
    assert client.get("/api/visual-memories").json()["visual_memories"][0]["object"] == "phone"
    assert client.delete("/api/visual-memories").json()["status"] == "cleared"


def test_settings_roundtrip(client):
    assert client.get("/api/settings").json()["GEMINI_MODEL"] == "gemini-2.5-flash"
    client.post("/api/settings", json={"LEARNING_ENABLED": False})
    from backend.config import settings
    assert settings.LEARNING_ENABLED is False
    client.post("/api/settings", json={"LEARNING_ENABLED": True})


def test_local_login_me_and_profile_update(client):
    login = client.post("/api/auth/local", json={"name": "Asha", "role": "Student"}).json()
    headers = {"Authorization": f"Bearer {login['token']}"}
    assert client.get("/api/auth/me", headers=headers).json()["user"]["name"] == "Asha"
    upd = client.patch("/api/auth/profile", headers=headers, json={"role": "Engineer"}).json()
    assert upd["user"]["role"] == "Engineer"


def test_me_requires_valid_token(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_google_login_success_creates_user(client, monkeypatch):
    async def fake_fetch(url, params=None, headers=None):
        if "tokeninfo" in url:
            return {"aud": "test-client-id.apps.googleusercontent.com"}
        return {"sub": "g-123", "name": "Shrestha", "email": "s@example.com", "picture": "http://x/p.png"}
    monkeypatch.setattr(auth, "_fetch_json", fake_fetch)
    r = client.post("/api/auth/google", json={"access_token": "abc"})
    assert r.status_code == 200 and r.json()["user"]["email"] == "s@example.com"
    # signing in again reuses the same account
    again = client.post("/api/auth/google", json={"access_token": "abc"}).json()
    assert again["user"]["id"] == r.json()["user"]["id"]


def test_google_login_rejects_token_for_other_app(client, monkeypatch):
    async def fake_fetch(url, params=None, headers=None):
        return {"aud": "someone-elses-client-id"}
    monkeypatch.setattr(auth, "_fetch_json", fake_fetch)
    assert client.post("/api/auth/google", json={"access_token": "abc"}).status_code == 401


def test_auth_config_exposes_client_id_only(client):
    cfg = client.get("/api/auth/config").json()
    assert cfg["google_enabled"] is True and "secret" not in str(cfg).lower()


def test_status_model_is_honest_without_api_keys(client):
    assert client.get("/api/status").json()["model"].startswith("offline")


def test_first_command_after_startup_is_already_warm(client):
    data = client.post("/api/chat", json={"text": "what time is it"}).json()
    assert data["latency_ms"] < 25
