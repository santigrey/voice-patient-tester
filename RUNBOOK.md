# Runbook

How to run the tester, check that a call worked, fix the failures we have actually hit, and
check the repo before it is shared. The story of each change is in `ITERATION_LOG.md`.

## 1. One-time setup

1. Accounts: LiveKit Cloud project, Deepgram key, Anthropic key, a carrier SIP connection
   (Telnyx here) with a verified caller ID. Telnyx's Trial tier can only dial its own verified
   number, so placing calls to any other number needs the Paid tier (see section 4).
2. `python3 -m venv ~/.venvs/voice-patient-tester` and
   `~/.venvs/voice-patient-tester/bin/pip install -r requirements.txt`. The venv stays outside
   the synced folder.
3. `mkdir -p ~/.config/voice-patient-tester`, copy `.env.example` there as `.env` and fill it
   in by hand. Never put real values in this folder.
4. `python -m src.setup_trunk` creates the LiveKit outbound trunk once and saves its id. It is
   safe to run again; it reuses the existing trunk.

## 2. Before a batch of calls

- `python -m unittest discover -s tests -v` (offline, no keys needed) and `ruff check src tests tools`.
- Check that the dial allowlist is what you expect: only the test line, unless `PROOF_NUMBER`
  is set for a single proof call. Clear `PROOF_NUMBER` again afterwards.
- Pace calls: Telnyx Paid allows 10 outbound calls per hour. Leave a few minutes between
  calls in a batch.

## 3. Run and verify a call

`python -m src.run_call 05` starts the worker, places the call, waits and stops the worker.
A good call has, in `calls/NN-scenario/`:

| File | What to check |
|---|---|
| `call.json` | `end_reason` is `bot-hung-up` or `callee-hung-up`; `error` is null; `latency` has a median under about 2 s |
| `audio-NN.ogg` | 2 channels; left = clinic, right = bot; both carry sound |
| `transcript-NN.txt` | turns alternate; times match the audio |
| `history.json` | every clinic turn is followed by a bot reply |

The worker's debug log for the last call is `.worker.log` (not tracked).

## 4. Failures we have hit, and the fix

| Symptom | Cause | Fix |
|---|---|---|
| `403 Can not make calls to non-verified numbers at this account level` | Telnyx Trial can only dial its one verified number | Upgrade the Telnyx account to Paid |
| `Only 1 active verified number is allowed at this account level` | Same Trial limit, when verifying a second number | Upgrade, or keep the one verified caller ID |
| Callee answers and hears nothing | Both sides waited for the other to speak | The bot says "Hello?" after 6 s of silence; proof calls open first |
| No `audio-NN.ogg` | Session recording was off | `record={"audio": True, ...}` in `session.start` (now in place) |
| Bot talks over the clinic's greeting, short "no problem" stops it mid-sentence | Reply pause too short; any word counted as an interruption | 1.0 s reply pause; interruptions need 3+ words and resume if false |
| Bot goes silent for the rest of the call; clinic asks "Are you still there?" | Claude Haiku 5.5 thinks by default; the thinking used the whole token budget, so the reply had no text | `PhoneClaude` turns thinking off. To confirm a repeat, replay `history.json` to the API and look for `stop_reason: max_tokens` with no text |
| Call runs to the 240 s cap after the clinic says goodbye | The bot had no way to hang up | `end_call` tool, plus hang-up after 35 s of silence on both sides |
| Call cut off while the clinic is "checking" | Silence hang-up of 15 s was shorter than the clinic's lookups (up to about 21 s) | Raised to 35 s |
| Transcript times do not match the audio | Times counted from the answer, but the recording starts earlier | Transcripts now use each turn's start time measured from the recording start |
| Bot invents details (a past procedure, a phone number) | The persona did not cover them | The prompt forbids invented history and gives the bot its own phone number |
| `Worker did not register in time` | Wrong LiveKit URL, key or secret, or no network | Check the three LiveKit values; a good start logs `registered worker` |

## 5. Before sharing the repo

1. `python tools/check_repo.py` must print `OK`. It checks every real secret value against all
   of git history, the tracked file list, banned names outside the call transcripts, and that
   the repo is private. It never prints a secret.
2. Search the transcripts for any personal detail that should not be there (for example a real
   date of birth) and mask it in the transcript if found.
3. Proof calls (`calls/proof-*`) are git-ignored and stay local.
4. Tests and lint pass (section 2).

## 6. Known limits

- The interruption scenario does not produce a true barge-in. The pipeline speaks only after
  the other side's turn ends, so talking over the agent would need a deliberate timed
  interjection.
- Calls 01 and 02 were made before per-turn timing was saved, so their transcript times are
  approximate end-of-turn times.
