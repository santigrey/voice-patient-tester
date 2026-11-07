"""Outbound caller agent.

A LiveKit worker. When dispatched it dials the number in the job metadata through the SIP
trunk, plays a patient with a goal, and writes the transcript, both-sides audio and a small
call.json into the call's folder under calls/.

Pipeline mode only: Deepgram STT -> Claude -> Deepgram TTS, with Silero VAD for turn taking.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

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
from livekit.plugins import anthropic, deepgram, silero

from . import config
from .scenarios import SCENARIOS, build_instructions

config.load_env()
log = logging.getLogger("patient-tester")

LLM_MODEL = "claude-haiku-5-5"
STT_MODEL = "nova-2"
TTS_MODEL = "aura-2-thalia-en"
CALLEE_IDENTITY = "callee"
SILENCE_BEFORE_HELLO = 6.0  # seconds of quiet after answer before the bot says hello

# Turn taking: Silero VAD decides when the other side is done; a short pause before replying
# keeps the patient from talking over the clinic agent, and interruptions stay enabled.
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
QUIET_HANGUP_SECONDS = 15.0  # both sides silent this long = the line is dead, hang up


def prewarm(proc: JobProcess) -> None:
    proc.userdata["vad"] = silero.VAD.load()


server = AgentServer(setup_fnc=prewarm)


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


def _stamp(seconds: float) -> str:
    seconds = max(0, int(seconds))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


@server.rtc_session(agent_name=config.AGENT_NAME)
async def entrypoint(ctx: JobContext) -> None:
    meta = json.loads(ctx.job.metadata or "{}")
    to = meta["to"]
    scenario = SCENARIOS[meta["scenario"]]
    call_dir = Path(meta["call_dir"])
    number = meta["number"]
    call_dir.mkdir(parents=True, exist_ok=True)

    # Safety rail: refuse anything that is not on the allowlist, before touching the phone.
    if to not in config.allowed_destinations():
        log.error("refusing to dial %s: not on the allowlist", to)
        _write_meta(call_dir, number, scenario.id, to, "refused-not-allowlisted", 0.0, None)
        ctx.shutdown()
        return

    await ctx.connect()

    session = AgentSession(
        stt=deepgram.STT(model=STT_MODEL, language="en-US"),
        llm=anthropic.LLM(model=LLM_MODEL, max_tokens=160),
        tts=deepgram.TTS(model=TTS_MODEL),
        vad=ctx.proc.userdata["vad"],
        turn_handling=TURN_HANDLING,
        user_away_timeout=QUIET_HANGUP_SECONDS,
    )

    lines: list[tuple[float, str, str]] = []
    answered_at: dict[str, float] = {}

    @session.on("conversation_item_added")
    def _on_item(ev) -> None:  # noqa: ANN001
        text = getattr(ev.item, "text_content", None)
        role = getattr(ev.item, "role", "")
        if not text or "t0" not in answered_at:
            return
        who = "PATIENT (bot)" if role == "assistant" else "CLINIC AGENT"
        lines.append((time.time() - answered_at["t0"], who, text.strip()))

    callee_gone = asyncio.Event()
    hangup = asyncio.Event()
    heard = {"other_side": False}

    @session.on("user_state_changed")
    def _on_user_state(ev) -> None:  # noqa: ANN001
        if ev.new_state == "speaking":
            heard["other_side"] = True
        elif ev.new_state == "away" and "t0" in answered_at:
            log.info("line quiet for %ss, hanging up", QUIET_HANGUP_SECONDS)
            hangup.set()

    @ctx.room.on("participant_disconnected")
    def _on_leave(p: rtc.RemoteParticipant) -> None:
        if p.identity == CALLEE_IDENTITY:
            callee_gone.set()

    await session.start(
        agent=PatientAgent(build_instructions(scenario), hangup),
        room=ctx.room,
        room_options=room_io.RoomOptions(participant_identity=CALLEE_IDENTITY),
        # Keep the both-sides audio; nothing is sent to the cloud (traces, logs, transcript off).
        record={"audio": True, "traces": False, "logs": False, "transcript": False},
    )

    end_reason = "callee-hung-up"
    sip_error: str | None = None
    try:
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
        answered_at["t0"] = time.time()
        if scenario.proof:
            # A friend picks up and waits, so the proof bot opens the conversation itself.
            session.generate_reply(
                instructions="Say your opening line now, as written in your instructions."
            )
        else:
            asyncio.create_task(_say_hello_if_silent(session, heard))
        gone = asyncio.create_task(callee_gone.wait())
        ended = asyncio.create_task(hangup.wait())
        done, pending = await asyncio.wait(
            {gone, ended}, timeout=config.MAX_CALL_SECONDS, return_when=asyncio.FIRST_COMPLETED
        )
        for t in pending:
            t.cancel()
        if ended in done and gone not in done:
            end_reason = "bot-hung-up"
        elif not done:
            end_reason = "max-duration-hangup"
    except api.SipCallError as e:
        end_reason = "call-failed"
        sip_error = f"{e.sip_status_code} {e.sip_status}"
        log.error("call failed: %s", sip_error)

    duration = time.time() - answered_at["t0"] if "t0" in answered_at else 0.0
    await session.aclose()

    # Hang up (ends the SIP leg if we are the one finishing) and collect the evidence.
    try:
        await ctx.api.room.delete_room(api.DeleteRoomRequest(room=ctx.room.name))
    except Exception:  # the room may already be gone
        pass

    _collect_audio(ctx, call_dir, number)
    _write_transcript(call_dir, number, scenario.slug, to, lines)
    _write_meta(call_dir, number, scenario.id, to, end_reason, duration, sip_error)
    ctx.shutdown()


async def _say_hello_if_silent(session: AgentSession, heard: dict) -> None:
    """A real caller says 'Hello?' if nobody speaks after the line is picked up.

    Call 01: this used to check for finished transcript lines, so it fired while the clinic
    was still mid-greeting. It now checks whether any speech was heard at all."""
    await asyncio.sleep(SILENCE_BEFORE_HELLO)
    if not heard["other_side"]:
        session.generate_reply(instructions="Nobody has spoken yet. Say a short 'Hello?' as a caller would.")


def _collect_audio(ctx: JobContext, call_dir: Path, number: str) -> None:
    """Copy the both-sides recording the session wrote (left = clinic, right = patient bot)."""
    src = getattr(ctx, "session_directory", None)
    if not src:
        return
    audio = Path(src) / "audio.ogg"
    if audio.is_file():
        shutil.copyfile(audio, call_dir / f"audio-{number}.ogg")


def _write_transcript(call_dir: Path, number: str, slug: str, to: str, lines) -> None:  # noqa: ANN001
    head = [
        f"Call {number} - {slug}",
        f"Dialed: {to}",
        f"Written: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "Timestamps are seconds from answer; audio-" + number + ".ogg has the same timeline.",
        "",
    ]
    body = [f"[{_stamp(t)}] {who}: {text}" for t, who, text in lines]
    (call_dir / f"transcript-{number}.txt").write_text("\n".join(head + body) + "\n")


def _write_meta(call_dir, number, scenario_id, to, end_reason, duration, sip_error) -> None:  # noqa: ANN001
    meta = {
        "call": number,
        "scenario": scenario_id,
        "dialed": to,
        "presented_number": os.environ.get("CALLER_ID", ""),
        "llm": LLM_MODEL,
        "stt": STT_MODEL,
        "tts": TTS_MODEL,
        "end_reason": end_reason,
        "duration_seconds": round(duration, 1),
        "sip_error": sip_error,
        "finished_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (call_dir / "call.json").write_text(json.dumps(meta, indent=2) + "\n")


if __name__ == "__main__":
    cli.run_app(server)
