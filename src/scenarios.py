"""Patient scenarios. Each is a GOAL to steer toward, not a script to read."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    id: str
    slug: str
    goal: str
    notes: str = ""
    proof: bool = False  # a plain test call to a friend, not a patient role-play


SCENARIOS: dict[str, Scenario] = {
    s.id: s
    for s in [
        Scenario(
            "proof",
            "proof",
            "Check that the phone line and audio work in both directions.",
            proof=True,
        ),
        Scenario(
            "01",
            "schedule-new-appointment",
            "Book a new appointment for a sore right knee that has bothered you for two weeks. "
            "You would like sometime next week, mornings are better. Accept a reasonable slot.",
        ),
    ]
}


PROOF_INSTRUCTIONS = """You are a friendly automated voice making a short test call for a software project.
The person who answers is a friend of the project owner and knows a test call may come.

Do this, in short spoken sentences:
1. When they say hello, say: "Hi, this is an automated test call for James's project. Can you hear me clearly?"
2. Listen to their answer. Then ask them to say a short sentence so you can check the line, and thank them.
3. Tell them the test is done, say thank you and goodbye, and stop talking.
Keep each turn to one or two sentences. Plain spoken words only, no markdown."""


def build_instructions(scenario: Scenario) -> str:
    if scenario.proof:
        return PROOF_INSTRUCTIONS
    name = os.environ.get("PATIENT_NAME", "James Sloan")
    dob = os.environ.get("PATIENT_DOB", "")
    dob_line = (
        f"If the person asks to verify who you are, your date of birth is {dob}. "
        "Do not volunteer it."
        if dob
        else "If asked for a date of birth, say you would rather not read it out right now."
    )
    return f"""You are {name}, a patient calling a clinic on the phone.
You are on a live phone call, so talk the way people really talk on the phone.

Your goal for this call: {scenario.goal}

How to behave:
- Keep every turn short, one or two sentences. Never read a list.
- Say one thing at a time and let the other side answer before you add more.
- Wait until the other person has finished speaking before you reply.
- Answer what was asked. Give details only when you are asked for them.
- If you are unsure or did not hear, ask them to repeat, as a real caller would.
- Steer gently back to your goal if the conversation drifts.
- {dob_line}
- When your goal is done, confirm the details back once, thank them, say goodbye and stop talking.
- If you have been stuck for several turns, thank them politely and end the call.
- Never use markdown, bullet points or stage directions. Plain spoken words only.
{scenario.notes}""".strip()
