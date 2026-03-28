import os
import logging
import asyncio
from dotenv import load_dotenv

# Load env variables before importing local modules that might rely on them
load_dotenv()

from src.infrastructure.repositories.mongo_repository import get_mongo_repository
from src.scheduler import BotScheduler
from src.utils.time_utils import get_current_time

# Configure basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

async def run_worker():
    logger.info("🚀 Starting Football ML Training Worker...")
    mongo_repo = get_mongo_repository()

    # Cron mode is the default for predictable daily runs.
    worker_mode = os.getenv("WORKER_MODE", "cron").strip().lower()
    scheduler = BotScheduler()

    if worker_mode == "loop":
        check_interval_seconds = int(os.getenv("WORKER_INTERVAL_SECONDS", "3600"))
        while True:
            logger.info(f"🔄 Starting loop training cycle at {get_current_time()}")
            try:
                await scheduler.run_daily_orchestrated_job()
                mongo_repo.save_training_result(
                    "worker_run",
                    {"status": "success", "message": "Orchestrated job completed successfully."},
                )
            except Exception as e:
                logger.error(f"❌ Error during training cycle: {e}")
                mongo_repo.save_training_result(
                    "worker_run",
                    {"status": "error", "error_message": str(e)},
                )

            logger.info(f"💤 Sleeping for {check_interval_seconds} seconds before next cycle...")
            await asyncio.sleep(check_interval_seconds)
        return

    run_immediate = os.getenv("WORKER_RUN_IMMEDIATE", "false").strip().lower() == "true"
    scheduler.start(run_immediate=run_immediate)
    logger.info("⏰ Cron scheduler activo (06:00 y 08:00 COT).")

    try:
        await asyncio.Event().wait()
    finally:
        scheduler.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logger.info("🛑 Worker stopped manually.")
