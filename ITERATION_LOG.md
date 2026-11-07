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
