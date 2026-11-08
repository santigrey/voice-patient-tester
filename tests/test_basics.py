"""Offline checks: safety rails, persona prompt, and that the pipeline objects build.

Run:  python -m unittest discover -s tests -v
No network and no real keys are used (dummy values are set for the plugin constructors).
"""
import os
import unittest

os.environ.setdefault("DEEPGRAM_API_KEY", "dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "dummy")
os.environ.pop("PROOF_NUMBER", None)

from src import config  # noqa: E402
from src.agent import TURN_HANDLING  # noqa: E402
from src.scenarios import SCENARIOS, build_instructions  # noqa: E402


class AllowlistTests(unittest.TestCase):
    def setUp(self):
        # The real secrets file may define PROOF_NUMBER; these tests must not depend on it.
        os.environ.pop("PROOF_NUMBER", None)

    def test_only_the_test_line_by_default(self):
        self.assertEqual(config.allowed_destinations(), {"+18054398008"})

    def test_proof_number_must_be_set_explicitly(self):
        os.environ["PROOF_NUMBER"] = "+15551230000"
        try:
            self.assertIn("+15551230000", config.allowed_destinations())
        finally:
            os.environ.pop("PROOF_NUMBER")

    def test_the_confirmation_screen_number_is_never_allowed(self):
        self.assertNotIn("+16156451400", config.allowed_destinations())


class PersonaTests(unittest.TestCase):
    def test_dob_only_when_configured_and_never_volunteered(self):
        os.environ["PATIENT_DOB"] = "TESTDOB"
        text = build_instructions(SCENARIOS["01"])
        self.assertIn("TESTDOB", text)
        self.assertIn("Do not volunteer it", text)
        os.environ.pop("PATIENT_DOB")
        self.assertNotIn("TESTDOB", build_instructions(SCENARIOS["01"]))

    def test_prompt_describes_wanted_behaviour(self):
        text = build_instructions(SCENARIOS["01"])
        self.assertIn("one or two sentences", text)


class PipelineTests(unittest.TestCase):
    def test_pipeline_objects_construct(self):
        from livekit.agents import AgentSession
        from livekit.plugins import anthropic, deepgram, silero

        session = AgentSession(
            stt=deepgram.STT(model="nova-2", language="en-US"),
            llm=anthropic.LLM(model="claude-haiku-5-5", max_tokens=160),
            tts=deepgram.TTS(model="aura-2-thalia-en"),
            vad=silero.VAD.load(),
            turn_handling=TURN_HANDLING,
        )
        self.assertIsNotNone(session)


class ProofScenarioTests(unittest.TestCase):
    def test_proof_prompt_says_it_is_automated_and_is_not_the_patient(self):
        text = build_instructions(SCENARIOS["proof"])
        self.assertIn("automated test call", text)
        self.assertNotIn("patient", text.lower().split("friendly automated voice")[0])


class PhoneClaudeTests(unittest.TestCase):
    def test_thinking_is_always_disabled(self):
        from unittest import mock

        from livekit.plugins import anthropic

        from src.agent import PhoneClaude

        seen = {}

        def fake_chat(self, **kwargs):
            seen.update(kwargs)

        with mock.patch.object(anthropic.LLM, "chat", fake_chat):
            PhoneClaude(model="claude-haiku-5-5").chat(chat_ctx=None)
        self.assertEqual(seen["extra_kwargs"]["thinking"], {"type": "disabled"})


class TranscriptTests(unittest.TestCase):
    HISTORY = {
        "items": [
            {"type": "message", "role": "user", "content": ["Hello, clinic."],
             "metrics": {"started_speaking_at": 110.0}},
            {"type": "function_call", "name": "end_call"},
            {"type": "message", "role": "assistant", "content": ["Hi, I need an appointment."],
             "metrics": {"started_speaking_at": 175.4, "e2e_latency": 1.2}},
            {"type": "message", "role": "assistant", "content": ["Thanks, bye."],
             "metrics": {"started_speaking_at": 190.0, "e2e_latency": 2.0}},
        ]
    }

    def test_times_are_measured_from_the_recording_start(self):
        from src.transcript import format_transcript, turns_from_history

        text = format_transcript(["Call 99"], turns_from_history(self.HISTORY), 100.0)
        self.assertIn("[00:10] CLINIC AGENT: Hello, clinic.", text)
        self.assertIn("[01:15] PATIENT (bot): Hi, I need an appointment.", text)
        self.assertNotIn("end_call", text)

    def test_latency_summary(self):
        from src.transcript import latency_summary

        self.assertEqual(
            latency_summary(self.HISTORY),
            {"bot_replies": 2, "e2e_latency_median_s": 1.6, "e2e_latency_max_s": 2.0},
        )


if __name__ == "__main__":
    unittest.main()
