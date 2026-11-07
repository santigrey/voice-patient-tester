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
        Scenario(
            "02",
            "reschedule-appointment",
            "You think you have an appointment coming up for your knee. Move it to a later day "
            "the following week, an afternoon if possible. If they cannot find it, ask what to do.",
        ),
        Scenario(
            "03",
            "cancel-appointment",
            "Cancel your upcoming knee appointment because the pain went away. Ask whether there "
            "is any cancellation fee.",
        ),
        Scenario(
            "04",
            "medication-refill",
            "Ask for a refill of your meloxicam, 15 milligrams, that the doctor prescribed for "
            "your knee. You have about three days left. Ask which pharmacy it will go to.",
        ),
        Scenario(
            "05",
            "office-hours-and-location",
            "Ask what the office hours are, whether they are open on Saturdays, and where the "
            "office is and where to park.",
        ),
        Scenario(
            "06",
            "insurance-question",
            "Ask whether they take Blue Cross Blue Shield PPO, and what you would pay for a "
            "visit if they do not.",
        ),
        Scenario(
            "07",
            "weekend-booking-edge-case",
            "Ask to book for this coming Sunday at 10 in the morning. If they offer Sunday, "
            "accept it. If they say they are closed, take the earliest weekday they offer.",
            notes="This is an edge case: you are testing whether they check office hours.",
        ),
        Scenario(
            "08",
            "interruption-edge-case",
            "Book an appointment for your knee, but change your mind partway: when they start "
            "offering a time, cut in and say you would rather see a different doctor if possible.",
            notes="This is an edge case: talking over the agent once is intended here.",
        ),
        Scenario(
            "09",
            "unclear-request-edge-case",
            "Start vague: say you need to 'sort out the thing from last time' without saying "
            "what it is. Only explain that you mean a refill after they ask a clarifying question.",
            notes="This is an edge case: you are testing how they handle an unclear request.",
        ),
        Scenario(
            "10",
            "two-requests-edge-case",
            "In one call, ask to book a knee appointment and also ask for a meloxicam refill. "
            "Make sure both get handled before you hang up.",
            notes="This is an edge case: two goals in one call.",
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
- Do not invent medical history. If asked something your goal does not cover, give a short,
  ordinary answer and stay consistent with it.
- If you are unsure or did not hear, ask them to repeat, as a real caller would.
- Steer gently back to your goal if the conversation drifts.
- {dob_line}
- If you hear a recorded notice (for example "this call may be recorded"), stay quiet and
  wait for a person to greet you.
- Short sounds like "okay" or "no problem" are not questions. Do not answer them.
- When your goal is done, confirm the details back once, thank them and say goodbye, then
  use the end_call tool.
- If the other side says goodbye, the line goes quiet, or you have been stuck for several
  turns, say a short goodbye and use the end_call tool.
- Never use markdown, bullet points or stage directions. Plain spoken words only.
{scenario.notes}""".strip()
