# Decisions

Plain-English log of the choices that matter, each with the tradeoff and the alternative.
Stage 1 draft; the numbers get filled in from real calls in Stage 4.

- **STT: Deepgram Nova-2.** Fast streaming and cheap, built for phone audio. Alternative:
  Nova-3 (newer, to compare on real calls) or AssemblyAI.
- **LLM: Claude Haiku 5.5.** Chosen for speed on short conversational turns. Alternative:
  Sonnet 5.5 (smarter, slower, about 20x the input price). Haiku 5.5 takes no temperature
  setting, so none is passed.
- **TTS: Deepgram Aura-2.** One vendor for both voice stages, low latency. Alternative:
  Cartesia or ElevenLabs (more natural voices, another key and cost).
- **Turn detection: Silero VAD with a 0.7 s pause.** Predictable and local. Alternative:
  a semantic turn-detector model (fewer interruptions, heavier).
- **Phone network: LiveKit SIP outbound trunk over Telnyx.** LiveKit's own phone numbers are
  inbound-only today. A verified caller ID lets the bot present a number the owner controls.
- **Latency:** streaming at every stage; no TTS until the LLM starts producing text.
