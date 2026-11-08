"""Turn the session's conversation history into a transcript and latency numbers.

Timestamps are measured from the start of the recording, using the moment each person
started speaking, so a time in the transcript is the same time in the audio file.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Any

CLINIC = "CLINIC AGENT"
BOT = "PATIENT (bot)"


@dataclass(frozen=True)
class Turn:
    started_at: float  # absolute (epoch seconds)
    speaker: str
    text: str


def turns_from_history(history: dict[str, Any]) -> list[Turn]:
    turns = []
    for item in history.get("items", []):
        if item.get("type") != "message" or item.get("role") not in ("user", "assistant"):
            continue
        text = " ".join(c for c in item.get("content", []) if isinstance(c, str)).strip()
        started = (item.get("metrics") or {}).get("started_speaking_at")
        if not text or started is None:
            continue
        speaker = BOT if item["role"] == "assistant" else CLINIC
        turns.append(Turn(float(started), speaker, text))
    return sorted(turns, key=lambda t: t.started_at)


def stamp(seconds: float) -> str:
    seconds = max(0, int(seconds))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def format_transcript(header: list[str], turns: list[Turn], recording_started_at: float) -> str:
    body = [f"[{stamp(t.started_at - recording_started_at)}] {t.speaker}: {t.text}" for t in turns]
    return "\n".join([*header, "", *body]) + "\n"


def latency_summary(history: dict[str, Any]) -> dict[str, float | int]:
    """End-to-end latency of the bot's replies: other side stops talking -> bot audio starts."""
    values = [
        float(m["e2e_latency"])
        for item in history.get("items", [])
        if item.get("type") == "message" and item.get("role") == "assistant"
        for m in [item.get("metrics") or {}]
        if m.get("e2e_latency") is not None
    ]
    if not values:
        return {"bot_replies": 0}
    return {
        "bot_replies": len(values),
        "e2e_latency_median_s": round(statistics.median(values), 2),
        "e2e_latency_max_s": round(max(values), 2),
    }
