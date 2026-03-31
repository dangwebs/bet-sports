#!/usr/bin/env python3
"""
Daemon wrapper to run `update_predictions_with_results.py` periodically.

Configure via env vars:
  UPDATER_INTERVAL_SEC (default 600)
  UPDATER_SCRIPT_PATH
    (default /workspace/backend/scripts/update_predictions_with_results.py)
  UPDATER_DAYS_BACK (default 3)
  UPDATER_DRY_RUN (default true)
"""

import logging
import os
import subprocess
import time

INTERVAL = int(os.getenv("UPDATER_INTERVAL_SEC", "600"))
SCRIPT_PATH = os.getenv(
    "UPDATER_SCRIPT_PATH",
    "/workspace/backend/scripts/update_predictions_with_results.py",
)
DAYS_BACK = int(os.getenv("UPDATER_DAYS_BACK", "3"))
DRY_RUN = os.getenv("UPDATER_DRY_RUN", "true").lower() in ("1", "true", "yes")


def run_once():
    try:
        cmd = ["python3", SCRIPT_PATH, "--days-back", str(DAYS_BACK)]
        if DRY_RUN:
            cmd.append("--dry-run")
        logging.info("Running updater script: %s", " ".join(cmd))
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        logging.info(
            "updater exit=%s stdout=%s stderr=%s",
            proc.returncode,
            proc.stdout.strip(),
            proc.stderr.strip(),
        )
        return proc.returncode
    except subprocess.TimeoutExpired:
        logging.error("updater run timed out")
        return 2
    except Exception:
        logging.exception("updater run failed")
        return 3


def main():
    logging.basicConfig(
        level=logging.INFO, format="[updater] %(asctime)s %(levelname)s: %(message)s"
    )
    logging.info(
        "Updater service started; interval=%ss days_back=%s dry_run=%s",
        INTERVAL,
        DAYS_BACK,
        DRY_RUN,
    )
    while True:
        run_once()
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
