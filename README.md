# Voice Patient Tester

A Python voice bot that phones a clinic's AI receptionist, plays a patient with a goal, and
records what happens so quality problems can be found and written up.

It runs in LiveKit Agents **pipeline mode**: speech-to-text, an LLM and text-to-speech are
separate components. No speech-to-speech models and no hosted voice-agent platforms.

| Stage | Provider |
|---|---|
| Speech to text | Deepgram Nova-2 |
| LLM | Claude Haiku 5.5 (Anthropic) |
| Text to speech | Deepgram Aura-2 |
| Turn taking | Silero VAD, 0.7 s pause, interruptions on |
| Phone network | LiveKit Cloud SIP outbound trunk to a Telnyx SIP connection |

## Setup (once per Mac)

```bash
python3 -m venv ~/.venvs/voice-patient-tester      # the venv lives outside the synced folder
~/.venvs/voice-patient-tester/bin/pip install -r requirements.txt
mkdir -p ~/.config/voice-patient-tester
cp .env.example ~/.config/voice-patient-tester/.env  # then fill in the values by hand
~/.venvs/voice-patient-tester/bin/python -m src.setup_trunk   # creates the LiveKit trunk once
```

Secrets are read from `~/.config/voice-patient-tester/.env` (or `VPT_ENV_FILE`). They are
never kept in this folder and never committed.

## Run a call

```bash
~/.venvs/voice-patient-tester/bin/python -m src.run_call 01
```

One command starts the worker, places the call, waits for it to end and stops the worker.
Output lands in `calls/NN-scenario/`: `audio-NN.ogg` (both sides, left = clinic, right =
patient bot), `transcript-NN.txt` and `call.json`.

## Safety rails

- The bot can only dial the one test line hardcoded in `src/config.py`. A second number is
  accepted only if you set `PROOF_NUMBER` yourself, for a single proof call.
- Calls hang up after 240 seconds.
- `python -m unittest discover -s tests -v` checks these rails offline.

## Files

`src/agent.py` the caller · `src/scenarios.py` patient goals · `src/run_call.py` one-command
runner · `src/setup_trunk.py` trunk setup · `ARCHITECTURE.md` · `DECISIONS.md` ·
`ITERATION_LOG.md` · `BUG_REPORT.md`
