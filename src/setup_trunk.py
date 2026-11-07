"""One-time: create (or reuse) the LiveKit outbound SIP trunk that points at the carrier."""
from __future__ import annotations

import asyncio
from pathlib import Path

from livekit import api

from . import config

TRUNK_NAME = "voice-patient-tester-outbound"
ENV_FILE = Path.home() / ".config" / "voice-patient-tester" / ".env"


async def main() -> None:
    config.load_env()
    caller_id = config.require("CALLER_ID")
    username = config.require("TELNYX_SIP_USERNAME")
    password = config.require("TELNYX_SIP_PASSWORD")

    async with api.LiveKitAPI() as lk:
        existing = await lk.sip.list_sip_outbound_trunk(api.ListSIPOutboundTrunkRequest())
        for trunk in existing.items:
            if trunk.name == TRUNK_NAME:
                print(f"Trunk already exists: {trunk.sip_trunk_id}")
                _remember(trunk.sip_trunk_id)
                return

        trunk = await lk.sip.create_sip_outbound_trunk(
            api.CreateSIPOutboundTrunkRequest(
                trunk=api.SIPOutboundTrunkInfo(
                    name=TRUNK_NAME,
                    address="sip.telnyx.com",
                    numbers=[caller_id],
                    auth_username=username,
                    auth_password=password,
                    # Telnyx matches the connection by username; sending it in the first INVITE
                    # makes it answer with a 407 challenge instead of guessing from the source IP.
                    headers={"X-Telnyx-Username": username},
                )
            )
        )
        print(f"Created trunk: {trunk.sip_trunk_id}")
        _remember(trunk.sip_trunk_id)


def _remember(trunk_id: str) -> None:
    """Append the (non-secret) trunk id to the local env file if it is not already there."""
    text = ENV_FILE.read_text() if ENV_FILE.is_file() else ""
    if "LIVEKIT_SIP_TRUNK_ID=" in text and f"LIVEKIT_SIP_TRUNK_ID={trunk_id}" not in text:
        lines = [ln for ln in text.splitlines() if not ln.startswith("LIVEKIT_SIP_TRUNK_ID=")]
        text = "\n".join(lines) + "\n"
    if f"LIVEKIT_SIP_TRUNK_ID={trunk_id}" not in text:
        ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
        ENV_FILE.write_text(text + f"LIVEKIT_SIP_TRUNK_ID={trunk_id}\n")
        print(f"Saved LIVEKIT_SIP_TRUNK_ID to {ENV_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
