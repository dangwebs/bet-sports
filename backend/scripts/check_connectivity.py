import logging
import os
import socket

from dotenv import load_dotenv
from pymongo import MongoClient

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("ConnectivityCheck")


def check_connectivity():
    load_dotenv()

    mongo_uri = os.getenv("MONGO_URI", "mongodb://admin:adminpassword@localhost:27017/")
    db_name = os.getenv("MONGO_DB_NAME", "bjj_betsports")

    logger.info("==================================================")
    logger.info("🔍 DIAGNOSTIC: MongoDB Connectivity Check")
    logger.info("==================================================")
    logger.info(f"📍 MONGO_URI: {mongo_uri}")
    logger.info(f"📂 MONGO_DB_NAME: {db_name}")

    # Try to extract hostname from URI
    try:
        # Simple extraction for mongodb://user:pass@host:port/
        host_part = mongo_uri.split("@")[-1].split(":")[0]
        port_part = mongo_uri.split("@")[-1].split(":")[1].split("/")[0]
        logger.info(f"🌐 Extracted Host: {host_part}, Port: {port_part}")

        # Test DNS resolution
        logger.info(f"🧪 Testing DNS resolution for '{host_part}'...")
        try:
            ip_addr = socket.gethostbyname(host_part)
            logger.info(f"✅ DNS lookup successful: {host_part} -> {ip_addr}")
        except socket.gaierror as e:
            logger.error(f"❌ DNS lookup FAILED for '{host_part}': {e}")
            if host_part == "mongodb":
                logger.warning(
                    (
                        "💡 Tip: If you are running on HOST, use 'localhost'. "
                        "If in Docker, ensure both containers are on the same network."
                    )
                )
            return

        # Test socket connection
        logger.info(f"🔌 Testing TCP socket connection to {host_part}:{port_part}...")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(3.0)
            res = s.connect_ex((host_part, int(port_part)))
            if res == 0:
                logger.info(f"✅ TCP connection to {host_part}:{port_part} successful!")
            else:
                logger.error(f"❌ TCP connection FAILED with error code: {res}")
                return

        # Test PyMongo connection
        logger.info(f"🍃 Testing PyMongo connection to {mongo_uri}...")
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
        client.admin.command("ping")
        logger.info("✅ MongoDB PING successful!")

        db = client[db_name]
        collections = db.list_collection_names()
        logger.info(
            f"✅ Successfully listed {len(collections)} collections in '{db_name}': "
            f"{collections}"
        )

    except Exception as e:
        logger.error(f"❌ Unexpected error during connectivity test: {e}")
    finally:
        logger.info("==================================================")


if __name__ == "__main__":
    check_connectivity()
