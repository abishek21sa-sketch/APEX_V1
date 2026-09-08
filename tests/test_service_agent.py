"""Tests for the /agent/chat endpoint. run_agent_turn is monkeypatched at the
service.main module level (where it's bound after import) rather than an
anthropic.Anthropic() client being faked, so only the one call that would
actually reach the network needs to be replaced. No *real* API key is ever
used -- but service.main.agent_chat now checks ANTHROPIC_API_KEY is set
before calling run_agent_turn at all, so any test relying on a mocked
run_agent_turn being reached must monkeypatch.setenv a fake key first, and
test_agent_chat_rejects_missing_api_key monkeypatch.delenvs it to test the
check itself. (Caught live: a missing key used to reach anthropic.Anthropic()
and fail deep inside request-header construction as a bare TypeError,
surfacing as an unhandled 500 instead of a clear error.)
"""

import pytest
anthropic = pytest.importorskip("anthropic", reason="optional APEX agent integration extra is not installed")
import httpx as httpx2
from fastapi.testclient import TestClient

import service.main as service_main
from agent.engineer_agent import AgentTurnResult, ToolCallRecord
from service.main import app

client = TestClient(app)


def test_agent_available_flag_is_true_in_this_environment():
    # Sanity check the route under test actually got registered (the agent extra
    # is installed here) rather than silently testing the 501 stub instead.
    assert service_main._AGENT_AVAILABLE


def test_agent_chat_returns_final_text_and_tool_calls(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-run-agent-turn-is-mocked-below")
    fake_result = AgentTurnResult(
        final_text="here's my recommendation",
        messages=[],
        tool_calls=[ToolCallRecord(name="get_design_space", input={}, result={"continuous": []}, is_error=False)],
        hops_used=1,
        forced_final=False,
    )
    monkeypatch.setattr(service_main, "run_agent_turn", lambda client, message: fake_result)

    response = client.post("/agent/chat", json={"message": "what's possible?"})
    assert response.status_code == 200
    body = response.json()
    assert body["final_text"] == "here's my recommendation"
    assert body["tool_calls"][0]["name"] == "get_design_space"
    assert body["tool_calls"][0]["is_error"] is False
    assert body["hops_used"] == 1
    assert body["forced_final"] is False


def test_agent_chat_rejects_empty_message():
    response = client.post("/agent/chat", json={"message": ""})
    assert response.status_code == 422


def test_agent_chat_rejects_missing_api_key(monkeypatch):
    # Do NOT monkeypatch run_agent_turn here -- the whole point is to reach the
    # real pre-flight check in service.main.agent_chat before any client/network
    # call would happen.
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    response = client.post("/agent/chat", json={"message": "hi"})
    assert response.status_code == 401
    assert "ANTHROPIC_API_KEY" in response.json()["detail"]


def _fake_httpx_request():
    return httpx2.Request("POST", "https://api.anthropic.com/v1/messages")


def test_agent_chat_maps_authentication_error_to_401(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-run-agent-turn-is-mocked-below")

    def raise_auth_error(client, message):
        response = httpx2.Response(401, request=_fake_httpx_request())
        raise anthropic.AuthenticationError("invalid key", response=response, body=None)

    monkeypatch.setattr(service_main, "run_agent_turn", raise_auth_error)
    response = client.post("/agent/chat", json={"message": "hi"})
    assert response.status_code == 401


def test_agent_chat_maps_generic_api_error_to_502(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-run-agent-turn-is-mocked-below")

    def raise_api_error(client, message):
        raise anthropic.APIConnectionError(request=_fake_httpx_request())

    monkeypatch.setattr(service_main, "run_agent_turn", raise_api_error)
    response = client.post("/agent/chat", json={"message": "hi"})
    assert response.status_code == 502
