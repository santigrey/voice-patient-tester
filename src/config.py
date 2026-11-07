"""Settings and the hard safety rails for outbound calls."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
CALLS_DIR = REPO_ROOT / "calls"

# The only number the bot may ever dial for a real test. Hardcoded on purpose.
TEST_LINE = "+18054398008"

AGENT_NAME = "patient-tester"
MAX_CALL_SECONDS = 240


def load_env() -> None:
    """Load secrets from outside the synced folder first, then a local .env."""
    for candidate in (
        os.environ.get("VPT_ENV_FILE"),
        Path.home() / ".config" / "voice-patient-tester" / ".env",
        REPO_ROOT / ".env",
    ):
        if candidate and Path(candidate).is_file():
            load_dotenv(candidate, override=False)


def allowed_destinations() -> set[str]:
    """The test line, plus one proof number only if PROOF_NUMBER is set explicitly."""
    allowed = {TEST_LINE}
    proof = os.environ.get("PROOF_NUMBER", "").strip()
    if proof:
        allowed.add(proof)
    return allowed


def require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"Missing {name}. Add it to ~/.config/voice-patient-tester/.env")
    return value
