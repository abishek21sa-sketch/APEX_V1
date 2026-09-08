"""Phase 9 demonstration: run the Vehicle Systems Engineer Agent on the platform
proposal's own worked example (or a custom prompt).

    python scripts/phase9_report.py
    python scripts/phase9_report.py "your own natural-language requirement here"

Requires ANTHROPIC_API_KEY (or another credential source the anthropic SDK
resolves automatically) to actually run -- this script checks for one and prints
a clear message instead of a confusing stack trace if none is available, rather
than pretending the agent ran. Everything downstream of the actual LLM call (the
seven tools, and the loop's control flow: tool dispatch, message threading,
max_hops, the forced-final-answer path) is covered by
tests/test_agent_tools.py and tests/test_agent_loop.py without needing a key --
this script is specifically for the part those tests can't cover: real model
behavior.
"""

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

import anthropic  # noqa: E402

from agent.engineer_agent import run_agent_turn  # noqa: E402

DEFAULT_PROMPT = (
    "Design a sub-$42k electric crossover capable of at least 310 miles of range "
    "while preserving 0-60 under six seconds. Show me the actual trade space, not "
    "just one answer, and tell me whether your recommendation would actually hold "
    "up in realistic conditions, not just on paper."
)


def main() -> None:
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        print(
            "No ANTHROPIC_API_KEY (or ANTHROPIC_AUTH_TOKEN) set -- the agent needs real "
            "credentials to make an actual LLM call. Set one and re-run."
        )
        raise SystemExit(1)

    prompt = " ".join(sys.argv[1:]) or DEFAULT_PROMPT
    client = anthropic.Anthropic()

    print(f"Prompt: {prompt}\n")
    result = run_agent_turn(client, prompt)

    print(f"--- {len(result.tool_calls)} tool call(s), {result.hops_used} hop(s), forced_final={result.forced_final} ---")
    for call in result.tool_calls:
        status = "ERROR" if call.is_error else "ok"
        print(f"  [{status}] {call.name}({call.input})")

    print(f"\n--- final answer ---\n{result.final_text}")


if __name__ == "__main__":
    main()
