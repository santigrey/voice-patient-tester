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

## Calls 04-11 - batch of the remaining scenarios
Observed: calls 04, 05, 06, 07 and 11 ran clean and the bot hung up itself. Calls 08 and 09
stalled the same way as call 02: the clinic spoke, the turn was committed, and the bot never
answered again. Call 10 ended after 15 s of quiet while the clinic was still looking up the
record.
Root cause (found by replaying call 08's conversation to the API): Claude Haiku 5.5 uses
extended thinking by default. On harder turns the thinking used the whole 160-token budget,
so the reply came back with stop_reason max_tokens and no text, and nothing was spoken.
Changed:
- Extended thinking is turned off for the call model (PhoneClaude). The stalled turn now
  answers in about 1 s, three times out of three. Token cap raised to 300 as a margin.
- Quiet-line hang-up raised from 15 s to 35 s; the clinic's lookups pause up to ~21 s.
- A test checks that thinking stays off.
Calls 02, 08, 09 and 10 are kept as evidence; the affected scenarios are re-run below.

## Calls 12-14 - re-runs of the stalled scenarios (thinking off)
Observed: all three ran to a natural end and the bot hung up itself. No stalls. Call 12
asked for Sunday and accepted the clinic's Monday offer. In call 14 the bot clarified the
vague request once asked. In call 13 the bot invented a phone number (555-0142) when asked
for the number on file, and the interruption it was meant to test never happened because
the clinic never got as far as offering a time.
Changed: the persona now knows its own phone number (the presented caller ID) and gives
that one if asked.

## Review before the write-up (code quality, repo, safety)
Found and fixed:
- Transcript times did not match the audio: they counted from the answer, but the recording
  starts earlier, so the audio ran about 7 to 9 s ahead. Transcripts are now written from the
  session history with each turn's start time measured from the recording start. Calls 03-14
  were rebuilt the same way; the alignment was checked against the bot's own channel and is
  within 0.35 s on every call. Calls 01-02 predate the history file, so their times were
  shifted onto the audio timeline and are marked as approximate end-of-turn times.
- call.json now records reply latency (median and max end-to-end, from the session metrics).
- Any unexpected error now still writes call.json, history and the transcript instead of
  losing the call; the hello timer is cancelled cleanly; call state lives in one small class.
- Lint added (ruff, config in pyproject.toml); clean. 10 offline tests pass.
- The proof number was removed from the local settings now that the proof call is done, so
  the only dialable number is the test line.
Repo checks: private; none of the real key values appear anywhere in git history; only the
expected files are tracked; no birth date; proof calls are not tracked; one author.
