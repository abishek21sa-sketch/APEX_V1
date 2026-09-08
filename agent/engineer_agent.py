"""The Vehicle Systems Engineer Agent: a manual Claude tool-calling loop over
tools.py's seven tools. Per the platform proposal, this agent "should not
directly control optimization" -- it can only affect the world through those
tool calls, each of which runs the real Phase 1-5 kernel, never a number the
model just states. Its job is translation and explanation: turn a natural-
language requirement into structured tool calls, then explain what the tools
returned.

The `client` parameter is duck-typed (anything with a `.messages.create(...)`
method matching the Anthropic SDK's shape) specifically so tests can inject a
fake client and verify the loop's control flow -- tool dispatch, message
threading, max_hops, the forced-final-answer path -- without an API key or a
live network call. See tests/test_agent_loop.py.

Forced-final-answer path (max_hops reached but Claude still wants a tool): use
`tool_choice: {"type": "none"}` with a *lower effort* level, not disabled
thinking. Disabling thinking on Claude Opus 5 has its own failure modes (a tool
call can leak into visible text instead of a proper tool_use block, or
`<thinking>` tags can leak into the response) -- this is current, model-specific
guidance, not the older "just disable thinking" fix from a previous model
generation.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Any, List, Optional

try:
    import anthropic as _anthropic  # optional runtime dependency; the loop itself is duck-typed
except ImportError:  # core tests can exercise the deterministic tool loop without the SDK
    _anthropic = None

from .tools import TOOL_DEFINITIONS, TOOL_DISPATCH

DEFAULT_MODEL = os.environ.get("APEX_AGENT_MODEL", "claude-opus-5")
MAX_TOKENS = 16000
DEFAULT_MAX_HOPS = 6

SYSTEM_PROMPT = """You are the APEX Vehicle Systems Engineer Agent, an engineering \
interface to a validated set of deterministic and probabilistic vehicle-design tools \
(a first-principles physics kernel, a mass/cost buildup, an NSGA2 multi-objective \
optimizer, and a Monte Carlo robust-design checker). You do not replace that \
engineering math and you do not directly control optimization -- every claim you make \
about a vehicle's mass, cost, performance, or feasibility must come from a tool result, \
never from your own estimate.

When a user states requirements in natural language (e.g. "a sub-$42k electric \
crossover with at least 310 miles of range and 0-60 under six seconds"), translate \
them into structured requirements using list_requirement_kinds's vocabulary, then call \
run_pareto_search or check_mission -- don't just describe what you would do.

Ground every proposed candidate in get_design_space's actual bounds and choices before \
proposing it. When asked whether a design is good, don't stop at check_mission's \
nominal-conditions answer -- call robust_check too and say plainly if a design that \
passes nominally would still fail under realistic payload/weather/tire-wear/battery-aging \
variation; that gap is a real, load-bearing distinction in this platform, not a footnote. \
When summarizing a Pareto frontier or a trade study, report the actual trade-offs (what \
you give up in one objective to gain in another) rather than picking a single "winner" \
-- the whole point of a Pareto search is that there isn't one.

Be concise and quantitative. Cite the specific numbers tools returned."""


@dataclass
class ToolCallRecord:
    name: str
    input: dict
    result: dict
    is_error: bool = False


@dataclass
class AgentTurnResult:
    final_text: str
    messages: List[dict]
    tool_calls: List[ToolCallRecord] = field(default_factory=list)
    hops_used: int = 0
    forced_final: bool = False


def _execute_tool(name: str, tool_input: dict) -> ToolCallRecord:
    dispatch = TOOL_DISPATCH.get(name)
    if dispatch is None:
        return ToolCallRecord(name=name, input=tool_input, result={"error": f"unknown tool {name!r}"}, is_error=True)
    try:
        return ToolCallRecord(name=name, input=tool_input, result=dispatch(tool_input))
    except Exception as exc:  # noqa: BLE001 -- tool errors must become a tool_result, not crash the loop
        return ToolCallRecord(name=name, input=tool_input, result={"error": str(exc)}, is_error=True)


def _final_text(response) -> str:
    return "".join(block.text for block in response.content if block.type == "text")


def run_agent_turn(
    client: Any,
    user_message: str,
    history: Optional[List[dict]] = None,
    model: str = DEFAULT_MODEL,
    max_hops: int = DEFAULT_MAX_HOPS,
) -> AgentTurnResult:
    messages = list(history) if history else []
    messages.append({"role": "user", "content": user_message})

    tool_calls: List[ToolCallRecord] = []
    hops = 0

    while True:
        response = client.messages.create(
            model=model,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
            thinking={"type": "adaptive"},
            output_config={"effort": "high"},
            messages=messages,
        )

        # None of this agent's tools are server-side tools (web_search, code
        # execution, ...), so stop_reason == "pause_turn" (a server-tool
        # iteration-limit signal) can't actually occur here; treating anything
        # other than "tool_use" as a completed turn is correct for this tool set
        # specifically -- revisit if a server-side tool is ever added.
        if response.stop_reason != "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            return AgentTurnResult(final_text=_final_text(response), messages=messages, tool_calls=tool_calls, hops_used=hops)

        hops += 1
        messages.append({"role": "assistant", "content": response.content})

        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
        if hops > max_hops:
            # Force a stop: answer every pending tool_use so the transcript stays
            # well-formed, then ask for a final answer with tool_choice disabled.
            forced_results = [
                {"type": "tool_result", "tool_use_id": b.id, "content": "Tool budget exhausted for this turn; summarize what's known so far.", "is_error": True}
                for b in tool_use_blocks
            ]
            messages.append({"role": "user", "content": forced_results})

            final_response = client.messages.create(
                model=model,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                tools=TOOL_DEFINITIONS,
                tool_choice={"type": "none"},
                thinking={"type": "adaptive"},
                output_config={"effort": "low"},
                messages=messages,
            )
            messages.append({"role": "assistant", "content": final_response.content})
            return AgentTurnResult(
                final_text=_final_text(final_response), messages=messages, tool_calls=tool_calls, hops_used=hops, forced_final=True
            )

        results = []
        for block in tool_use_blocks:
            record = _execute_tool(block.name, block.input)
            tool_calls.append(record)
            results.append({"type": "tool_result", "tool_use_id": block.id, "content": _serialize(record.result), "is_error": record.is_error})
        messages.append({"role": "user", "content": results})


def _serialize(result: dict) -> str:
    return json.dumps(result)
