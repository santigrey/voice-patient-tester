"""Outbound caller agent.

A LiveKit worker. When dispatched it dials the number in the job metadata through the SIP
trunk, plays a patient with a goal, and writes the both-sides audio, a transcript, the full
conversation history and a small call.json into the call's folder under calls/.

Pipeline mode only: Deepgram STT -> Claude -> Deepgram TTS, with Silero VAD for turn taking.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from livekit import api, rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    RunContext,
    cli,
    function_tool,
    room_io,
)
from livekit.agents.types import NOT_GIVEN, NotGivenOr
from livekit.agents.utils import is_given
from livekit.plugins import anthropic, deepgram, silero

from . import config
from .scenarios import SCENARIOS, Scenario, build_instructions
from .transcript import format_transcript, latency_summary, turns_from_history

config.load_env()
log = logging.getLogger("patient-tester")

LLM_MODEL = "claude-haiku-5-5"
STT_MODEL = "nova-2"
TTS_MODEL = "aura-2-thalia-en"
CALLEE_IDENTITY = "callee"
SILENCE_BEFORE_HELLO = 6.0  # seconds of quiet after answer before the bot says hello

# Turn taking: Silero VAD decides when the other side is done.
TURN_HANDLING = {
    "turn_detection": "vad",
    # Call 01: replying after 0.7 s cut into the clinic's greeting. Wait a full second.
    "endpointing": {"min_delay": 1.0},
    # Call 01: two-word backchannels ("No prob", "No worries") stopped the bot mid-sentence.
    # Only three or more words count as a real interruption, and a false one resumes.
    "interruption": {
        "enabled": True,
        "min_words": 3,
        "resume_false_interruption": True,
        "false_interruption_timeout": 1.5,
    },
}
# Both sides silent this long = the line is dead, hang up. Call 10: 15 s cut the call while
# the clinic was still looking something up (its lookups pause up to ~21 s), so wait 35 s.
QUIET_HANGUP_SECONDS = 35.0


class PhoneClaude(anthropic.LLM):
    """Claude with extended thinking off.

    Calls 02, 08 and 09 stalled: Haiku 5.5 thinks by default, and on harder turns the thinking
    used the whole token budget, so the reply came back with no text (stop_reason max_tokens)
    and the bot said nothing. With thinking off the same turn answers in about a second.
    """

    def chat(self, *, extra_kwargs: NotGivenOr[dict[str, Any]] = NOT_GIVEN, **kwargs: Any):
        merged: dict[str, Any] = {"thinking": {"type": "disabled"}}
        if is_given(extra_kwargs):
            merged.update(extra_kwargs)
        return super().chat(extra_kwargs=merged, **kwargs)


class PatientAgent(Agent):
    """The patient, plus one tool so it can hang up like a real caller."""

    def __init__(self, instructions: str, hangup: asyncio.Event) -> None:
        super().__init__(instructions=instructions)
        self._hangup = hangup

    @function_tool
    async def end_call(self, ctx: RunContext) -> str:
        """Hang up the phone. Use it after you have said goodbye, or when the other side has
        said goodbye or the line has gone dead."""
        await ctx.wait_for_playout()
        self._hangup.set()
        return "Call ended."


@dataclass
class CallState:
    """Everything one call needs to remember while it runs."""

    recording_started_at: float = 0.0
    answered_at: float | None = None
    ended_at: float | None = None
    heard_other_side: bool = False
    callee_gone: asyncio.Event = field(default_factory=asyncio.Event)
    hangup: asyncio.Event = field(default_factory=asyncio.Event)
    end_reason: str = "callee-hung-up"
    error: str | None = None


def prewarm(proc: JobProcess) -> None:
    proc.userdata["vad"] = silero.VAD.load()


server = AgentServer(setup_fnc=prewarm)


@server.rtc_session(agent_name=config.AGENT_NAME)
async def entrypoint(ctx: JobContext) -> None:
    meta = json.loads(ctx.job.metadata or "{}")
    to: str = meta["to"]
    scenario = SCENARIOS[meta["scenario"]]
    number: str = meta["number"]
    call_dir = Path(meta["call_dir"])
    call_dir.mkdir(parents=True, exist_ok=True)

    # Safety rail: refuse anything that is not on the allowlist, before touching the phone.
    if to not in config.allowed_destinations():
        log.error("refusing to dial %s: not on the allowlist", to)
        _write_meta(call_dir, number, scenario, to, CallState(end_reason="refused-not-allowlisted"), {})
        ctx.shutdown()
        return

    await ctx.connect()
    state = CallState()
    session = AgentSession(
        stt=deepgram.STT(model=STT_MODEL, language="en-US"),
        llm=PhoneClaude(model=LLM_MODEL, max_tokens=300),
        tts=deepgram.TTS(model=TTS_MODEL),
        vad=ctx.proc.userdata["vad"],
        turn_handling=TURN_HANDLING,
        user_away_timeout=QUIET_HANGUP_SECONDS,
    )

    @session.on("user_state_changed")
    def _on_user_state(ev: Any) -> None:
        if ev.new_state == "speaking":
            state.heard_other_side = True
        elif ev.new_state == "away" and state.answered_at is not None:
            log.info("line quiet for %ss, hanging up", QUIET_HANGUP_SECONDS)
            state.hangup.set()

    @ctx.room.on("participant_disconnected")
    def _on_leave(p: rtc.RemoteParticipant) -> None:
        if p.identity == CALLEE_IDENTITY:
            state.callee_gone.set()

    hello_task: asyncio.Task[None] | None = None
    try:
        # The recorder starts with the session, so transcript times are measured from here.
        state.recording_started_at = time.time()
        await session.start(
            agent=PatientAgent(build_instructions(scenario), state.hangup),
            room=ctx.room,
            room_options=room_io.RoomOptions(participant_identity=CALLEE_IDENTITY),
            # Keep the both-sides audio locally; nothing is uploaded (traces, logs, transcript off).
            record={"audio": True, "traces": False, "logs": False, "transcript": False},
        )
        await ctx.api.sip.create_sip_participant(
            api.CreateSIPParticipantRequest(
                room_name=ctx.room.name,
                sip_trunk_id=config.require("LIVEKIT_SIP_TRUNK_ID"),
                sip_call_to=to,
                participant_identity=CALLEE_IDENTITY,
                participant_name="Clinic line",
                wait_until_answered=True,
            )
        )
        state.answered_at = time.time()
        if scenario.proof:
            # A friend picks up and waits, so the proof bot opens the conversation itself.
            session.generate_reply(instructions="Say your opening line now, as written in your instructions.")
        else:
            hello_task = asyncio.create_task(_say_hello_if_silent(session, state))
        await _wait_for_end(state)
    except api.SipCallError as e:
        state.end_reason = "call-failed"
        state.error = f"{e.sip_status_code} {e.sip_status}"
        log.error("call failed: %s", state.error)
    except Exception as e:  # record any other failure instead of losing the call
        state.end_reason = "error"
        state.error = f"{type(e).__name__}: {e}"
        log.exception("call aborted")
    finally:
        state.ended_at = time.time()
        if hello_task is not None:
            hello_task.cancel()
        await _finish(ctx, session, state, call_dir, number, scenario, to)


async def _wait_for_end(state: CallState) -> None:
    gone = asyncio.create_task(state.callee_gone.wait())
    ended = asyncio.create_task(state.hangup.wait())
    done, pending = await asyncio.wait(
        {gone, ended}, timeout=config.MAX_CALL_SECONDS, return_when=asyncio.FIRST_COMPLETED
    )
    for task in pending:
        task.cancel()
    if ended in done and gone not in done:
        state.end_reason = "bot-hung-up"
    elif not done:
        state.end_reason = "max-duration-hangup"


async def _say_hello_if_silent(session: AgentSession, state: CallState) -> None:
    """A real caller says 'Hello?' if nobody speaks after the line is picked up.

    Call 01: this used to check for finished transcript lines, so it fired while the clinic
    was still mid-greeting. It now checks whether any speech was heard at all.
    """
    await asyncio.sleep(SILENCE_BEFORE_HELLO)
    if not state.heard_other_side:
        session.generate_reply(instructions="Nobody has spoken yet. Say a short 'Hello?' as a caller would.")


async def _finish(
    ctx: JobContext,
    session: AgentSession,
    state: CallState,
    call_dir: Path,
    number: str,
    scenario: Scenario,
    to: str,
) -> None:
    """Hang up and write the evidence: history, audio, transcript and call.json."""
    history = session.history.to_dict()
    await session.aclose()  # flushes the recording
    try:
        await ctx.api.room.delete_room(api.DeleteRoomRequest(room=ctx.room.name))
    except Exception:  # the room may already be gone
        log.debug("room already closed")

    (call_dir / "history.json").write_text(json.dumps(history, indent=2, default=str) + "\n")
    _collect_audio(ctx, call_dir, number)
    header = [
        f"Call {number} - {scenario.slug}",
        f"Dialed: {to}",
        f"Written: {datetime.now(UTC).isoformat(timespec='seconds')}",
        f"Times are mm:ss into audio-{number}.ogg, when each person started speaking.",
    ]
    turns = turns_from_history(history)
    (call_dir / f"transcript-{number}.txt").write_text(
        format_transcript(header, turns, state.recording_started_at)
    )
    _write_meta(call_dir, number, scenario, to, state, latency_summary(history))
    ctx.shutdown()


def _collect_audio(ctx: JobContext, call_dir: Path, number: str) -> None:
    """Copy the both-sides recording the session wrote (left = clinic, right = patient bot)."""
    audio = Path(ctx.session_directory) / "audio.ogg"
    if audio.is_file():
        shutil.copyfile(audio, call_dir / f"audio-{number}.ogg")
    else:
        log.warning("no recording found at %s", audio)


def _write_meta(
    call_dir: Path,
    number: str,
    scenario: Scenario,
    to: str,
    state: CallState,
    latency: dict[str, float | int],
) -> None:
    duration = (state.ended_at or time.time()) - state.answered_at if state.answered_at else 0.0
    meta = {
        "call": number,
        "scenario": scenario.id,
        "dialed": to,
        "presented_number": os.environ.get("CALLER_ID", ""),
        "llm": LLM_MODEL,
        "stt": STT_MODEL,
        "tts": TTS_MODEL,
        "end_reason": state.end_reason,
        "duration_seconds": round(duration, 1),
        "error": state.error,
        "latency": latency,
        "finished_utc": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    (call_dir / "call.json").write_text(json.dumps(meta, indent=2) + "\n")


if __name__ == "__main__":
    cli.run_app(server)
