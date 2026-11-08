"""Pre-submission repo check. Run from the repo root:  python tools/check_repo.py

Fails (exit 1) if any real secret value from the local env file appears anywhere in git
history, if an unexpected file is tracked, if a banned name appears outside the call
transcripts, or if the repo is not private. Prints names only, never secret values.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ENV_FILE = Path(os.environ.get("VPT_ENV_FILE", Path.home() / ".config/voice-patient-tester/.env"))
SECRET_KEYS = (
    "LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "DEEPGRAM_API_KEY",
    "ANTHROPIC_API_KEY", "TELNYX_SIP_USERNAME", "TELNYX_SIP_PASSWORD",
)
ALLOWED = re.compile(
    r"^(src/|tests/|tools/|calls/\d{2}-[a-z0-9-]+/|\.gitignore$|\.env\.example$|requirements\.txt$"
    r"|pyproject\.toml$|[A-Z_]+\.md$)"
)
BANNED = re.compile(r"pretty ?good|pgai", re.IGNORECASE)


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def main() -> int:
    failures: list[str] = []

    secrets = {}
    for line in ENV_FILE.read_text().splitlines() if ENV_FILE.is_file() else []:
        key, _, value = line.partition("=")
        if key in SECRET_KEYS and value.strip():
            secrets[key] = value.strip()
    revs = git("rev-list", "--all").split()
    for key, value in secrets.items():
        found = subprocess.run(["git", "grep", "-I", "-l", "-F", value, *revs], capture_output=True, text=True)
        if found.stdout.strip():
            failures.append(f"secret {key} appears in git history")
    print(f"secrets: {len(secrets)} values checked across {len(revs)} commits")

    unexpected = [f for f in git("ls-files").splitlines() if not ALLOWED.match(f)]
    failures += [f"unexpected tracked file: {f}" for f in unexpected]

    for f in git("ls-files").splitlines():
        if f.startswith("calls/"):
            continue  # the clinic says its own name on the calls
        if BANNED.search(f) or (Path(f).is_file() and BANNED.search(Path(f).read_text(errors="ignore"))):
            failures.append(f"banned name in {f}")

    visibility = subprocess.run(
        ["gh", "repo", "view", "--json", "visibility", "-q", ".visibility"], capture_output=True, text=True
    ).stdout.strip()
    if visibility != "PRIVATE":
        failures.append(f"repo visibility is {visibility or 'unknown'}, expected PRIVATE")

    for f in failures:
        print("FAIL", f)
    print("OK" if not failures else f"{len(failures)} problem(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
