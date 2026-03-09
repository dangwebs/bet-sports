import os
import time
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
    
    # Initialize the scheduler which contains the training orchestration logic
    # In the new architecture, this isn't a cron-based scheduler as much as it's the 
    # execution pipeline for training. We will trigger it in a continuous loop.
    scheduler = BotScheduler()
    
    # Simple continuous loop for the worker.
    # It will run the data extraction and training cycle, then sleep for an interval.
    # We can control the check interval via an environment variable.
    check_interval_seconds = int(os.getenv("WORKER_INTERVAL_SECONDS", "3600")) # Defaults to 1 hour
    
    while True:
        logger.info(f"🔄 Starting new training cycle at {get_current_time()}")
        try:
            # We call the heavily integrated training pipeline (orchestrated job)
            await scheduler.run_daily_orchestrated_job()
            
            # Log successful run to MongoDB
            mongo_repo.save_training_result("worker_run", {
                "status": "success",
                "message": "Orchestrated job completed successfully."
            })
            
            logger.info("✅ Training cycle completed successfully.")
        except Exception as e:
            logger.error(f"❌ Error during training cycle: {e}")
            mongo_repo.save_training_result("worker_run", {
                "status": "error",
                "error_message": str(e)
            })
            
        logger.info(f"💤 Sleeping for {check_interval_seconds} seconds before next cycle...")
        await asyncio.sleep(check_interval_seconds)

if __name__ == "__main__":
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logger.info("🛑 Worker stopped manually.")
