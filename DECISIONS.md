# Decisions

The choices that shape how the calls sound, each with the reason, the tradeoff and the
alternatives considered. Latency figures are from 103 bot replies across calls 03 to 16
(read from each call's `history.json`).

## Speech to text: Deepgram Nova-2
- **Why:** streaming, fast and accurate on phone audio; one vendor for both speech
  directions keeps setup to one key.
- **Tradeoff:** it mishears some names (provider names came out several ways). That mostly
  affects our transcripts, not the conversation; anything quoted in the bug report was
  re-checked against the audio with Nova-3.
- **Alternatives:** Nova-3 (newer; used for the bug-report cross-check, a candidate to switch
  to), AssemblyAI, Whisper (batch, too slow for live turns).

## LLM: Claude Haiku 5.5, extended thinking off
- **Why:** the patient's job is short, sensible turns with low delay. Haiku is the fastest
  Claude model and cheap; median time to first token was 0.61 s.
- **Tradeoff, learned the hard way:** Haiku 5.5 thinks before answering by default. On harder
  turns the thinking used the whole token budget and the reply came back empty, so the bot went
  silent mid-call (calls 02, 08, 09). Turning thinking off fixed it; the stalled turn then
  answered in about a second, every time. The cost is less deliberation on unusual turns,
  which a patient on the phone does not need.
- **Alternatives:** Sonnet 5.5 (better reasoning, slower and pricier per turn), keeping thinking
  on with a much larger token budget (worked in a replay but was slower: 1.8 s against 0.8 to 1.5 s with thinking off).

## Text to speech: Deepgram Aura-2
- **Why:** streams audio quickly (median 0.14 s to first audio) and shares the key with STT.
- **Tradeoff:** a clear but plainly synthetic voice.
- **Alternatives:** Cartesia or ElevenLabs (more natural voices, another vendor, more cost).

## Turn detection and interruptions: Silero VAD, 1.0 s pause, 3-word interruptions
- **Why:** predictable and local. The first real call showed what was wrong with the defaults:
  replying after 0.7 s cut into the clinic's recorded notice, and short backchannels ("No
  prob", "No worries") stopped the bot mid-sentence. A 1.0 s pause and a rule that only three
  or more words count as an interruption (false ones resume) fixed both.
- **Tradeoff:** the extra pause is about a third of the bot's reply time. A semantic
  end-of-turn model could shorten it, at the cost of another model in the loop.
- **Known limit:** the bot never talks over the clinic, because it only speaks after the other
  side's turn ends. The interruption scenario (calls 09, 13, 15) therefore tested a change of
  mind mid-booking, not a true barge-in. Making the bot cut in would need a deliberately timed
  interjection; it was left out to keep scope to what the calls needed.

## Phone network: LiveKit SIP outbound trunk to Telnyx, one verified caller ID
- **Why:** LiveKit's own phone numbers are inbound-only today, so outbound needs a carrier
  trunk. Telnyx lets an existing number be verified as caller ID instead of buying one, so
  every call presents the same number.
- **Tradeoff:** Telnyx's free Trial tier can only dial its one verified number (calls to any
  other number fail with a 403), so the account had to be upgraded with a small payment.
- **Alternatives:** Twilio or Plivo trunks (same idea, different account limits).

## Latency: how it was kept low
- Every stage streams: speech is transcribed as it arrives, Claude's reply streams token by
  token, and speech synthesis starts on the first words.
- Thinking is off (see above), and replies are capped at 300 tokens and kept to one or two
  sentences by the prompt.
- The worker runs a pre-loaded voice-activity model, so no model loads during a call.
- **Result:** median end-to-end reply time 1.54 s (other side stops talking to bot audio
  starting), 90th percentile 2.16 s, worst 3.21 s. About 1.0 s of that is the deliberate
  pause before replying, chosen to stop the bot talking over the clinic.
- Each call's `call.json` records its own median and maximum.

## Other choices
- **Recording:** the session's built-in both-sides recorder, written locally as one stereo
  OGG per call; nothing is uploaded.
- **Secrets:** read from `~/.config/voice-patient-tester/.env`, outside the synced project
  folder; `tools/check_repo.py` confirms none ever reached git history.
