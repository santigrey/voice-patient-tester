"""Run one call end to end: start the worker, dispatch the call, wait, stop the worker.

    python -m src.run_call 01              # scenario 01 to the test line
    python -m src.run_call 01 --proof      # same scenario to PROOF_NUMBER (never the test line)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
import time
from datetime import datetime, timezone

from livekit import api

from . import config
from .scenarios import SCENARIOS


def next_call_number() -> int:
    existing = [p.name[:2] for p in config.CALLS_DIR.glob("[0-9][0-9]-*") if p.is_dir()]
    return max((int(n) for n in existing if n.isdigit()), default=0) + 1


async def dispatch(scenario_id: str, to: str, number: str, call_dir: str) -> None:
    room = f"call-{number}-{datetime.now(timezone.utc):%H%M%S}"
    async with api.LiveKitAPI() as lk:
        await lk.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(
                agent_name=config.AGENT_NAME,
                room=room,
                metadata=json.dumps(
                    {"to": to, "scenario": scenario_id, "number": number, "call_dir": call_dir}
                ),
            )
        )


def main() -> None:
    config.load_env()
    ap = argparse.ArgumentParser()
    ap.add_argument("scenario", choices=sorted(SCENARIOS))
    ap.add_argument("--proof", action="store_true", help="dial PROOF_NUMBER instead of the test line")
    args = ap.parse_args()

    to = config.require("PROOF_NUMBER") if args.proof else config.TEST_LINE
    if to not in config.allowed_destinations():
        raise SystemExit(f"{to} is not on the allowlist")

    scenario = SCENARIOS[args.scenario]
    number = f"{next_call_number():02d}"
    call_dir = config.CALLS_DIR / f"{number}-{scenario.slug}"
    call_dir.mkdir(parents=True, exist_ok=True)

    log_path = config.REPO_ROOT / ".worker.log"
    with open(log_path, "w") as log:
        worker = subprocess.Popen(
            [sys.executable, "-m", "src.agent", "start"],
            cwd=config.REPO_ROOT, stdout=log, stderr=subprocess.STDOUT,
        )
        try:
            _wait_registered(log_path, worker)
            asyncio.run(dispatch(scenario.id, to, number, str(call_dir)))
            print(f"Call {number} dispatched to {to}. Waiting for it to finish...")
            _wait_done(call_dir, worker)
        finally:
            worker.terminate()
            try:
                worker.wait(timeout=15)
            except subprocess.TimeoutExpired:
                worker.kill()

    result = call_dir / "call.json"
    print(result.read_text() if result.is_file() else "No call.json written; see .worker.log")


def _wait_registered(log_path, worker, timeout: float = 45.0) -> None:  # noqa: ANN001
    start = time.time()
    while time.time() - start < timeout:
        if worker.poll() is not None:
            raise SystemExit("Worker exited early; see .worker.log")
        if "registered worker" in log_path.read_text(errors="ignore"):
            return
        time.sleep(1)
    raise SystemExit("Worker did not register in time; see .worker.log")


def _wait_done(call_dir, worker, timeout: float = config.MAX_CALL_SECONDS + 90) -> None:  # noqa: ANN001
    start = time.time()
    while time.time() - start < timeout:
        if (call_dir / "call.json").is_file() or worker.poll() is not None:
            return
        time.sleep(2)


if __name__ == "__main__":
    main()
