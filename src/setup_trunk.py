"""One-time: create (or reuse) the LiveKit outbound SIP trunk that points at the carrier."""
from __future__ import annotations

import asyncio

from livekit import api

from . import config

TRUNK_NAME = "voice-patient-tester-outbound"


async def main() -> None:
    config.load_env()
    caller_id = config.require("CALLER_ID")
    username = config.require("TELNYX_SIP_USERNAME")
    password = config.require("TELNYX_SIP_PASSWORD")

    async with api.LiveKitAPI() as lk:
        existing = await lk.sip.list_outbound_trunk(api.ListSIPOutboundTrunkRequest())
        trunk = next((t for t in existing.items if t.name == TRUNK_NAME), None)
        if trunk:
            print(f"Trunk already exists: {trunk.sip_trunk_id}")
            _remember(trunk.sip_trunk_id)
            return

        trunk = await lk.sip.create_outbound_trunk(
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
    """Store the (non-secret) trunk id in the local env file, replacing any older one."""
    lines = [ln for ln in config.ENV_FILE.read_text().splitlines() if not ln.startswith("LIVEKIT_SIP_TRUNK_ID=")]
    config.ENV_FILE.write_text("\n".join([*lines, f"LIVEKIT_SIP_TRUNK_ID={trunk_id}"]) + "\n")
    print(f"Saved LIVEKIT_SIP_TRUNK_ID to {config.ENV_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
