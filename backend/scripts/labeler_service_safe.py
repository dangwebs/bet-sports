#!/usr/bin/env python3
"""
Safer labeler service wrapper for use in Docker/compose overrides.
- handles SIGTERM/SIGINT gracefully
- forwards configurable args to `label_finished_matches.py`
- configurable timeout and interval via env vars
"""

import logging
import os
import signal
import subprocess
import time

INTERVAL = int(os.getenv("LABELER_INTERVAL_SEC", "600"))
SCRIPT_PATH = os.getenv(
    "LABELER_SCRIPT_PATH", "/workspace/backend/scripts/label_finished_matches.py"
)

_stop_requested = False


def _handle_signal(signum, frame):
    global _stop_requested
    logging.info("Received signal %s, shutting down labeler service", signum)
    _stop_requested = True


def run_once(cmd, timeout_sec=300):
    try:
        logging.info("Running labeler command: %s", " ".join(cmd))
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec)
        logging.info(
            "labeler exit=%s stdout=%s stderr=%s",
            proc.returncode,
            proc.stdout.strip(),
            proc.stderr.strip(),
        )
        return proc.returncode
    except subprocess.TimeoutExpired:
        logging.error("labeler run timed out after %ss", timeout_sec)
        return 2
    except Exception:
        logging.exception("labeler run failed")
        return 3


def _bool_env(name, default=False):
    v = os.getenv(name)
    if v is None:
        return default
    return str(v).lower() in ("1", "true", "yes", "on")


def main():
    global INTERVAL
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="[labeler] %(asctime)s %(levelname)s: %(message)s",
    )

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    labeler_limit = os.getenv("LABELER_LIMIT")
    labeler_retries = os.getenv("LABELER_RETRIES")
    labeler_dry_run = _bool_env("LABELER_DRY_RUN", False)
    labeler_timeout = int(os.getenv("LABELER_TIMEOUT_SEC", "300"))

    cmd = ["python3", SCRIPT_PATH]
    if labeler_limit:
        cmd += ["--limit", str(labeler_limit)]
    if labeler_retries:
        cmd += ["--retries", str(labeler_retries)]
    if labeler_dry_run:
        cmd.append("--dry-run")

    logging.info(
        "Labeler service started; interval=%ss cmd=%s", INTERVAL, " ".join(cmd)
    )

    while not _stop_requested:
        run_once(cmd, timeout_sec=labeler_timeout)

        if _stop_requested:
            break

        remaining = INTERVAL
        # sleep in small increments so we can shutdown quickly
        while remaining > 0 and not _stop_requested:
            time.sleep(min(1, remaining))
            remaining -= 1


if __name__ == "__main__":
    main()
