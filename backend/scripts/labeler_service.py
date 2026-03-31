#!/usr/bin/env python3
"""
Small daemon wrapper that runs `label_finished_matches.py` periodically.

Use with Docker or as a long-running process in the worker container.
Configure interval via `LABELER_INTERVAL_SEC` (default 600s).
"""

import logging
import os
import subprocess
import time

INTERVAL = int(os.getenv("LABELER_INTERVAL_SEC", "600"))
SCRIPT_PATH = os.getenv(
    "LABELER_SCRIPT_PATH", "/workspace/backend/scripts/label_finished_matches.py"
)


def run_once():
    try:
        logging.info("Running labeler script: %s", SCRIPT_PATH)
        proc = subprocess.run(
            ["python3", SCRIPT_PATH], capture_output=True, text=True, timeout=300
        )
        logging.info(
            "labeler exit=%s stdout=%s stderr=%s",
            proc.returncode,
            proc.stdout.strip(),
            proc.stderr.strip(),
        )
        return proc.returncode
    except subprocess.TimeoutExpired:
        logging.error("labeler run timed out")
        return 2
    except Exception:
        logging.exception("labeler run failed")
        return 3


def main():
    logging.basicConfig(
        level=logging.INFO, format="[labeler] %(asctime)s %(levelname)s: %(message)s"
    )
    logging.info("Labeler service started; interval=%ss", INTERVAL)
    while True:
        run_once()
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
