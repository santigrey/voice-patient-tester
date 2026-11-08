# Architecture

One command (`python -m src.run_call 05`) starts a LiveKit Agents worker on this machine, asks
LiveKit Cloud to dispatch it into a fresh room with the scenario and the number to dial, and
waits. The worker joins the room and starts a voice session in pipeline mode: Deepgram Nova-2
turns the other side's speech into text, Claude Haiku 5.5 decides what the patient says next,
and Deepgram Aura-2 speaks it, with Silero voice-activity detection deciding when the other
side has finished. It then asks LiveKit to place the call over an outbound SIP trunk to a
Telnyx connection that presents one verified caller ID. The clinic's agent answers and speaks
first; the patient listens, waits for a one-second pause, and answers in short turns that
steer toward the scenario's goal. The patient is a goal plus behaviour rules, not a script,
so it can follow wherever the clinic takes the conversation, and it ends the call itself with
an `end_call` tool once the goal is met or the call is going nowhere.

When the call ends the worker writes everything needed to judge it: a both-sides recording
(clinic on the left channel, bot on the right), a transcript stamped with mm:ss into that
recording, the session's full conversation history, and `call.json` with the outcome and the
bot's reply latency. Safety is kept in a few plain places: a hard-coded allowlist checked both
before dispatch and again in the worker, a 240-second cap, a hang-up after 35 seconds of
silence, and secrets read from a file outside the project folder. Why each piece was chosen,
what else was considered, and what the calls showed is in `DECISIONS.md`; how each version
changed after listening to the calls is in `ITERATION_LOG.md`.
