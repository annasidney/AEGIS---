import pytest

from backend.agent import router as router_module
from backend.agent.router import router

pytestmark = pytest.mark.unit


@pytest.fixture()
def calls(monkeypatch):
    """Record registry calls instead of touching the real desktop."""
    log = []

    async def fake_execute(name, args, require_confirmation=False):
        log.append((name, args))
        return {"success": True, "verified": True, "result": {"message": f"{name} ok"}}

    monkeypatch.setattr(router_module.registry, "execute", fake_execute)
    return log


async def test_greeting_is_instant(calls):
    r = await router.route_and_execute("hello")
    assert r["tool"] == "greeting" and calls == []


async def test_math_is_solved_locally(calls):
    r = await router.route_and_execute("2*2")
    assert r["tool"] == "calculate_math" and "4" in r["response"]


async def test_time_uses_system_clock_tool(calls):
    r = await router.route_and_execute("what time is it")
    assert r["tool"] == "get_system_time" and calls[0][0] == "get_system_time"


async def test_youtube_play(calls):
    r = await router.route_and_execute("play Believer on YouTube")
    assert r["tool"] == "youtube_play" and calls[0] == ("youtube_play", {"song": "Believer"})


async def test_open_application(calls):
    r = await router.route_and_execute("open notepad")
    assert calls[0] == ("open_application", {"app_name": "notepad"})
    assert r["tool"] == "open_application"


async def test_reminder_with_time_creates_it(calls):
    await router.route_and_execute("remind me tomorrow at 5 pm to submit assignment")
    assert calls[0][0] == "create_reminder"
    assert calls[0][1] == {"text": "submit assignment", "time_str": "tomorrow at 5 pm"}


async def test_reminder_without_time_asks_when(calls):
    r = await router.route_and_execute("remind me to call mom")
    assert r["response"] == "When should I remind you?"
    assert r["pending_reminder_task"] == "call mom" and calls == []


async def test_brightness_set(calls):
    await router.route_and_execute("set brightness to 40")
    assert calls[0] == ("set_brightness", {"action": "set", "level": 40})


async def test_lock_screen(calls):
    await router.route_and_execute("lock my screen")
    assert calls[0][0] == "lock_screen"


async def test_unknown_request_falls_through_to_llm(calls):
    assert await router.route_and_execute("plan a surprise itinerary for my cousin") is None


async def test_deterministic_dispatch_is_under_5ms(calls):
    import time
    await router.route_and_execute("hello")  # warm up regex cache
    t0 = time.perf_counter()
    for _ in range(20):
        await router.route_and_execute("hello")
        await router.route_and_execute("2*2")
    avg_ms = (time.perf_counter() - t0) * 1000 / 40
    assert avg_ms < 5, f"router too slow: {avg_ms:.2f} ms"
