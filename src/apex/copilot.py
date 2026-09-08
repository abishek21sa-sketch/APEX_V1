"""Small, auditable APEX copilot boundary.

The deterministic answer is always available.  Gemini is an optional narration layer and
never becomes the source of vehicle physics, optimization, or release decisions.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"


def status() -> dict[str, Any]:
    return {
        "provider": "Google Gemini",
        "model": DEFAULT_MODEL,
        "key_present": bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")),
        "deterministic_fallback": True,
        "temperature": 0,
        "claim_boundary": "APEX physics and surrogate metrics are engineering evidence, not production vehicle telemetry.",
    }


def _deterministic_answer(message: str, context: dict[str, Any]) -> str:
    q = message.casefold()
    if any(k in q for k in ("range", "miles", "battery")):
        focus = "Use the Evaluate and Robust Check workspaces to compare range against mass, battery capacity, and uncertainty."
    elif any(k in q for k in ("cost", "cheap", "price", "manufactur")):
        focus = "Use Evaluate for the deterministic cost breakdown, then confirm the candidate remains feasible under the mission requirements."
    elif any(k in q for k in ("surrogate", "model", "uncertainty", "gp", "random forest")):
        focus = "Use Surrogate Lab to compare holdout error; the selected model accelerates exploration but does not replace the physics evaluator."
    elif any(k in q for k in ("pareto", "optimiz", "design")):
        focus = "Start with the Pareto or Robust workspace, inspect the constraint certificate, and keep the final choice human-gated."
    else:
        focus = "Start with Evaluate for a point design, then use Robust Check and Surrogate Lab before treating a candidate as review-ready."
    return (
        "Deterministic APEX engineering readout\n\n"
        f"Question: {message.strip()}\n\n"
        f"Recommended path: {focus}\n"
        f"Current evidence: {context.get('evidence', 'default design space and physics evaluator available')}\n"
        "Boundary: no production telemetry is available here; every recommendation requires engineer review."
    )


def _gemini_answer(message: str, context: dict[str, Any]) -> str:
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    prompt = (
        "You are the APEX vehicle-systems engineering copilot. Use only the supplied deterministic "
        "context. Never invent physics, telemetry, certification, or production claims. Explain that "
        "APEX remains review-only. Return concise engineering guidance.\n\n"
        f"Context: {json.dumps(context, sort_keys=True)}\nQuestion: {message.strip()}"
    )
    body = {
        "system_instruction": {"parts": [{"text": "APEX copilot; deterministic engineering evidence is authoritative."}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0, "seed": 42, "maxOutputTokens": 700},
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{DEFAULT_MODEL}:generateContent"
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        payload = json.loads(response.read().decode("utf-8"))
    parts = payload.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    text = "\n".join(str(part.get("text", "")) for part in parts if part.get("text"))
    if not text.strip():
        raise RuntimeError("Gemini returned no visible text")
    return text.strip()


def build_response(message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = context or {}
    deterministic = _deterministic_answer(message, context)
    if not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
        return {**status(), "answer": deterministic, "provider": "deterministic", "model": "rule-based", "fallback": True}
    try:
        return {"answer": _gemini_answer(message, context), "provider": "Google Gemini", "model": DEFAULT_MODEL, "fallback": False, **status()}
    except (OSError, urllib.error.URLError, json.JSONDecodeError, RuntimeError) as exc:
        return {**status(), "answer": deterministic, "provider": "deterministic-fallback", "model": "rule-based", "fallback": True, "error": type(exc).__name__}
