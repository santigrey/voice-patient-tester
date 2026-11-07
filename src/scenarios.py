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


SCENARIOS: dict[str, Scenario] = {
    s.id: s
    for s in [
        Scenario(
            "01",
            "schedule-new-appointment",
            "Book a new appointment for a sore right knee that has bothered you for two weeks. "
            "You would like sometime next week, mornings are better. Accept a reasonable slot.",
        ),
    ]
}


def build_instructions(scenario: Scenario) -> str:
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
