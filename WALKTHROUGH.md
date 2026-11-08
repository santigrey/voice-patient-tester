# Walkthrough

Notes for the two videos and for interview questions. Webcam on, own voice, no company name
on screen or in speech: say "the clinic's agent" or "the test line".

## Video 1: walkthrough (3 minutes, hard limit)

| Time | Show | Say |
|---|---|---|
| 0:00-0:20 | README | What it is: a bot that phones a clinic's AI receptionist as a patient, holds a real conversation, and records it so problems can be found. |
| 0:20-0:50 | Play 15 s of `calls/03-reschedule-appointment/audio-03.ogg` from 00:20 | Let them hear it: natural turns, the bot steering to a booking. |
| 0:50-1:30 | `ARCHITECTURE.md`, then `src/agent.py` (the session setup) | The pipeline: Deepgram STT, Claude Haiku, Deepgram TTS, VAD, LiveKit SIP to Telnyx. One command per call. |
| 1:30-2:10 | `ITERATION_LOG.md`: the stall entry | The best bug was ours: the bot went silent mid-call. Replaying the conversation to the API showed Haiku spending its whole budget thinking and returning no text. Thinking off, fixed, re-ran the three calls. |
| 2:10-2:45 | `BUG_REPORT.md`, findings 1 to 3 | The clinic accepts a mismatched birth date "for demo purposes", invents one, and every transfer to support ends the call. Each is cited by call and second, checked against the audio. |
| 2:45-3:00 | `DECISIONS.md`, latency section | Median reply 1.54 s; a third of it is a deliberate pause so the bot does not talk over the clinic. |

## Video 2: debugging with AI (screen recording, prompts visible)

Re-run a real problem from this project live rather than a staged one. Good candidate: the
silent-bot stall.

1. Show the symptom: open `calls/08-weekend-booking-edge-case/transcript-08.txt`, the clinic
   asking "Are you still there?". Prompt the assistant with the transcript and ask why the bot
   stopped answering.
2. Ask it to read the worker log and `history.json` for that call; point out that turns were
   committed but no reply was generated.
3. Ask it to replay the conversation up to that turn against the model API and print the
   stop reason. It shows `max_tokens` with only a thinking block.
4. Ask for the smallest fix; review the `PhoneClaude` change; run the tests; show the same turn
   now answering in about a second.
5. Close on the re-run call (12) that went through cleanly.

Keep each prompt on screen long enough to read.

## Interview talking points
- **Why pipeline and not speech-to-speech:** required by the brief, and it makes every stage
  measurable and swappable; the latency numbers come straight from that separation.
- **The stall:** found from symptoms, not guessed; proved by replay; fixed with one setting;
  confirmed live. The broken calls stay in the repo as evidence.
- **Turn taking:** the first call showed the problems (talking over a recorded notice,
  backchannels interrupting); two numbers fixed them, both cited to that call.
- **What I would do next:** a semantic end-of-turn model to cut the 1.0 s pause, Nova-3 for
  STT, and a timed interjection to test true barge-in.
- **Honest limits:** no true barge-in; calls 01 and 02 have approximate timestamps; the
  transcripts are our speech-to-text, so exact quotes were re-checked against the audio.
