# Iteration log

Newest entry last. Each entry says what was observed, what changed and why.

## Stage 1 - scaffold (before any real call)
- Built the pipeline: Deepgram Nova-2 STT, Claude Haiku 5.5, Deepgram Aura-2 TTS, Silero VAD.
- Patient behaviour is a short goal-steering prompt (short turns, wait for the other side,
  one thing at a time), not a script.
- Recording uses the session's built-in both-sides recorder; the transcript is written from
  conversation events with seconds-from-answer timestamps.
- Offline tests cover the destination allowlist, the persona prompt and that the pipeline
  objects construct. Nothing has been tested on a live call yet.
- Left for the first real calls: turn-taking pause length, latency, TTS voice choice, and
  whether Nova-3 beats Nova-2 on phone audio.

## Proof calls (owner's own phone, not committed)
- First proof call: silence. The bot waited for the callee to speak first, and the callee
  waited too. Fix: on a proof call the bot opens; on real calls it says "Hello?" if nobody
  speaks. Audio was not saved because session recording was off. Fix: record audio locally.
- Second proof call: two-way audio confirmed on both channels, transcript written.
  First bot words came about 7 s after answer.

## Call 01 - schedule-new-appointment (first real call)
Observed:
- The bot answered the recorded "this call may be recorded" notice and talked over the
  clinic's greeting. Short backchannels ("No prob", "No worries") kept interrupting it, so
  the opening was 20 seconds of false starts.
- The "Hello?" fallback fired during the greeting: it checked for finished transcript
  lines, which only appear after the other side stops talking.
- After the clinic's transfer ended in a goodbye message, the bot had no way to hang up and
  talked into silence until the 240 s limit.
- The bot read the patient's date of birth aloud to correct one the clinic invented. The
  transcript is masked; the persona now uses a placeholder birth date.
Changed:
- Reply pause 0.7 s -> 1.0 s. Interruptions need 3+ words; false interruptions resume.
- Prompt: stay quiet through recorded notices; do not answer "okay"-style sounds.
- New end_call tool, and the bot hangs up after 15 s of silence on both sides.
- Hello fallback now checks whether any speech was heard, and waits 6 s.
- Scenarios 02-10 added: reschedule, cancel, refill, hours and location, insurance, and four
  labelled edge cases (weekend booking, interruption, unclear request, two requests).

## Call 02 - reschedule-appointment (bot stalled)
Observed: after the clinic said it found no appointment and offered to book a new one, the
bot never spoke again. The clinic asked twice, then "Are you still there?", then hung up.
The audio confirms the bot's channel is silent from about 40 s on. The INFO log showed no
error, so the cause is not known yet.
Changed: every call now saves history.json (the full conversation, including tool calls)
and the worker runs with debug logging, so a repeat of this stall can be diagnosed.

## Call 03 - reschedule-appointment (retry)
Observed: clean opening (the bot waited out the greeting), a full conversation, a booking
for Thursday 2 PM, and the bot ended the call itself with the end_call tool. The bot
invented a past knee procedure when asked the reason for the visit.
Changed: the prompt now says not to invent medical history and to keep any improvised
answer short and consistent.
