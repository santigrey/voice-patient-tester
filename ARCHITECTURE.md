# Architecture

`run_call` starts a LiveKit Agents worker, then asks LiveKit to dispatch it to a new room
with the number to dial and the scenario. The worker joins the room, starts a voice session
(Deepgram speech-to-text, Claude, Deepgram text-to-speech, Silero voice-activity detection)
and then asks LiveKit to dial the number over the SIP trunk. When the clinic's agent answers
it speaks first; the patient bot listens, waits for the pause, and replies with a short
turn that steers toward the scenario goal. When the call ends the worker writes the
both-sides audio, a timestamped transcript and `call.json`.

Full per-choice reasoning with alternatives is in `DECISIONS.md` and is finished in Stage 4.
