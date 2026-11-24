import pytest

from backend.agent import llm_agent as la
from backend.agent.llm_agent import AegisAgent

pytestmark = pytest.mark.unit


def test_schema_sanitizer_strips_unsupported_keys():
    clean = AegisAgent._to_gemini_schema({
        "type": "object", "additionalProperties": False,
        "properties": {"x": {"type": "string", "default": "a", "description": "d"}},
        "required": ["x"],
    })
    assert "additionalProperties" not in clean
    assert clean["properties"]["x"] == {"type": "string", "description": "d"}


def test_function_declarations_include_tools_and_search():
    names = [d["name"] for d in AegisAgent()._gemini_function_declarations()]
    assert {"get_system_time", "create_reminder", "set_brightness", "search_web"} <= set(names)


class FakeResp:
    def __init__(self, status, body):
        self.status_code, self._body, self.text = status, body, str(body)

    def json(self):
        return self._body


def fake_client(responses):
    seq = iter(responses)

    class _Client:
        def __init__(self, *a, **k): ...
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, url, headers=None, json=None):
            return next(seq)
    return _Client


async def test_react_loop_calls_tool_then_answers(monkeypatch):
    monkeypatch.setattr(la.settings, "GEMINI_API_KEY", "k")
    tool_turn = {"candidates": [{"content": {"role": "model", "parts": [
        {"functionCall": {"name": "get_system_time", "args": {}}}]}}]}
    final_turn = {"candidates": [{"content": {"role": "model", "parts": [{"text": "It is 9 PM."}]}}]}
    monkeypatch.setattr(la.httpx, "AsyncClient", fake_client([FakeResp(200, tool_turn), FakeResp(200, final_turn)]))
    agent = AegisAgent()
    res = await agent._run_gemini_react("what's the time?")
    assert res["response"] == "It is 9 PM."
    assert [s["tool"] for s in res["steps"]] == ["get_system_time"]


async def test_react_loop_returns_none_on_api_error(monkeypatch):
    monkeypatch.setattr(la.settings, "GEMINI_API_KEY", "k")
    monkeypatch.setattr(la.httpx, "AsyncClient", fake_client([FakeResp(500, {"error": "boom"})]))
    assert await AegisAgent()._run_gemini_react("hi") is None


async def test_process_message_falls_back_offline_when_gemini_fails(monkeypatch):
    monkeypatch.setattr(la.settings, "GEMINI_API_KEY", "k")
    monkeypatch.setattr(la.settings, "OPENROUTER_API_KEY", "")
    monkeypatch.setattr(la.httpx, "AsyncClient", fake_client([FakeResp(503, {})]))
    res = await AegisAgent().process_message("thanks a lot")
    assert "welcome" in res["response"].lower()
