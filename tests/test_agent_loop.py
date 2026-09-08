"""Tests the agent loop's control flow (tool dispatch, message threading,
max_hops, the forced-final-answer path) with a fake Anthropic client, so they
run without an API key or a live network call. Real LLM behavior isn't and
can't be verified by these tests -- see agent/README.md for what is and isn't
covered.
"""

import pytest

from agent.engineer_agent import run_agent_turn


class FakeTextBlock:
    type = "text"

    def __init__(self, text):
        self.text = text


class FakeToolUseBlock:
    type = "tool_use"

    def __init__(self, id, name, input):
        self.id = id
        self.name = name
        self.input = input


class FakeResponse:
    def __init__(self, content, stop_reason):
        self.content = content
        self.stop_reason = stop_reason


class FakeMessagesAPI:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        # Snapshot messages: engineer_agent.py keeps mutating the same list object
        # after this call returns (appending the assistant's reply, etc.), so
        # storing the reference as-is would make calls[i]["messages"] reflect
        # whatever the list looks like *now*, not what was actually sent.
        kwargs = {**kwargs, "messages": list(kwargs["messages"])}
        self.calls.append(kwargs)
        return self._responses[len(self.calls) - 1]


class FakeClient:
    def __init__(self, responses):
        self.messages = FakeMessagesAPI(responses)


def test_single_turn_with_no_tool_calls():
    client = FakeClient([FakeResponse([FakeTextBlock("hello there")], "end_turn")])
    result = run_agent_turn(client, "hi")
    assert result.final_text == "hello there"
    assert result.tool_calls == []
    assert result.hops_used == 0
    assert not result.forced_final


def test_single_tool_call_then_final_answer():
    client = FakeClient(
        [
            FakeResponse([FakeToolUseBlock("t1", "get_design_space", {})], "tool_use"),
            FakeResponse([FakeTextBlock("the battery ranges from 30 to 120 kWh")], "end_turn"),
        ]
    )
    result = run_agent_turn(client, "what's the battery range?")

    assert result.hops_used == 1
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "get_design_space"
    assert not result.tool_calls[0].is_error
    assert result.final_text == "the battery ranges from 30 to 120 kWh"

    # messages: [0] original user question, [1] assistant's tool_use, [2] our
    # tool_result reply -- must be threaded back as a user message with the
    # matching tool_use_id.
    tool_result_message = result.messages[2]
    assert tool_result_message["role"] == "user"
    assert tool_result_message["content"][0]["tool_use_id"] == "t1"
    assert tool_result_message["content"][0]["type"] == "tool_result"


def test_unknown_tool_name_becomes_an_error_result_not_a_crash():
    client = FakeClient(
        [
            FakeResponse([FakeToolUseBlock("t1", "not_a_real_tool", {})], "tool_use"),
            FakeResponse([FakeTextBlock("ok")], "end_turn"),
        ]
    )
    result = run_agent_turn(client, "do something")
    assert result.tool_calls[0].is_error
    assert "unknown tool" in result.tool_calls[0].result["error"]


def test_tool_dispatch_exception_becomes_an_error_result_not_a_crash():
    client = FakeClient(
        [
            # evaluate_candidate with a missing required field should raise inside
            # the tool, not propagate out of the agent loop.
            FakeResponse([FakeToolUseBlock("t1", "evaluate_candidate", {"battery_capacity_kwh": 70.0})], "tool_use"),
            FakeResponse([FakeTextBlock("ok")], "end_turn"),
        ]
    )
    result = run_agent_turn(client, "evaluate this")
    assert result.tool_calls[0].is_error
    assert "error" in result.tool_calls[0].result


def test_parallel_tool_calls_are_all_dispatched_and_returned_in_one_message():
    client = FakeClient(
        [
            FakeResponse(
                [
                    FakeToolUseBlock("t1", "get_design_space", {}),
                    FakeToolUseBlock("t2", "list_requirement_kinds", {}),
                ],
                "tool_use",
            ),
            FakeResponse([FakeTextBlock("done")], "end_turn"),
        ]
    )
    result = run_agent_turn(client, "look up two things")

    assert len(result.tool_calls) == 2
    assert {c.name for c in result.tool_calls} == {"get_design_space", "list_requirement_kinds"}

    tool_result_message = result.messages[2]  # [0] user question, [1] assistant's two tool_uses, [2] our reply
    assert tool_result_message["role"] == "user"
    assert len(tool_result_message["content"]) == 2  # both results in the SAME message
    assert {block["tool_use_id"] for block in tool_result_message["content"]} == {"t1", "t2"}


def test_max_hops_forces_a_final_answer_with_tool_choice_none_and_lower_effort():
    tool_use_response = FakeResponse([FakeToolUseBlock("t1", "get_design_space", {})], "tool_use")
    final_response = FakeResponse([FakeTextBlock("here's what I found so far")], "end_turn")
    # max_hops=2: iterations 1,2 dispatch normally; iteration 3 exceeds the budget
    # and forces a 4th (final) call.
    client = FakeClient([tool_use_response, tool_use_response, tool_use_response, final_response])

    result = run_agent_turn(client, "keep looking things up", max_hops=2)

    assert result.forced_final
    assert result.final_text == "here's what I found so far"
    assert len(client.messages.calls) == 4

    forced_call_kwargs = client.messages.calls[-1]
    assert forced_call_kwargs["tool_choice"] == {"type": "none"}
    assert forced_call_kwargs["output_config"] == {"effort": "low"}
    # Current guidance for Opus 5: don't disable thinking to force a final answer
    # (it has its own failure modes) -- stay adaptive, just lower effort.
    assert forced_call_kwargs["thinking"] == {"type": "adaptive"}


def test_max_hops_answers_pending_tool_uses_before_the_forced_final_call():
    tool_use_response = FakeResponse([FakeToolUseBlock("pending-id", "get_design_space", {})], "tool_use")
    final_response = FakeResponse([FakeTextBlock("summary")], "end_turn")
    client = FakeClient([tool_use_response, final_response])

    result = run_agent_turn(client, "go", max_hops=0)

    assert result.forced_final
    # messages: [0] user question, [1] assistant's pending tool_use, [2] our
    # budget-exhausted tool_result reply (before the forced final call), [3] the
    # forced final assistant answer.
    pending_answer_message = result.messages[2]
    assert pending_answer_message["role"] == "user"
    assert pending_answer_message["content"][0]["tool_use_id"] == "pending-id"
    assert pending_answer_message["content"][0]["is_error"] is True


def test_conversation_history_threads_across_turns():
    client1 = FakeClient([FakeResponse([FakeTextBlock("first answer")], "end_turn")])
    result1 = run_agent_turn(client1, "first question")

    client2 = FakeClient([FakeResponse([FakeTextBlock("second answer")], "end_turn")])
    result2 = run_agent_turn(client2, "second question", history=result1.messages)

    sent_messages = client2.messages.calls[0]["messages"]
    assert sent_messages[0]["content"] == "first question"
    assert sent_messages[-1]["content"] == "second question"
    assert result2.final_text == "second answer"


def test_default_model_is_opus_5_when_no_env_override_is_set(monkeypatch):
    monkeypatch.delenv("APEX_AGENT_MODEL", raising=False)
    import importlib

    import agent.engineer_agent as engineer_agent_module

    importlib.reload(engineer_agent_module)
    try:
        assert engineer_agent_module.DEFAULT_MODEL == "claude-opus-5"

        client = FakeClient([FakeResponse([FakeTextBlock("ok")], "end_turn")])
        engineer_agent_module.run_agent_turn(client, "hi")
        assert client.messages.calls[0]["model"] == "claude-opus-5"
    finally:
        importlib.reload(engineer_agent_module)  # restore whatever the real environment implies
