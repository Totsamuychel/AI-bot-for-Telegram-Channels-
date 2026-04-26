import asyncio
import logging
from admin_bot.database import engine, Base
from admin_bot.config import DATABASE_URL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def reset_db():
    logger.info(f"Connecting to database: {DATABASE_URL}")
    try:
        async with engine.begin() as conn:
            logger.info("Dropping all tables...")
            await conn.run_sync(Base.metadata.drop_all)
            logger.info("Recreating all tables with the new schema...")
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database successfully reset!")
    except Exception as e:
        logger.error(f"Error resetting database: {e}")

if __name__ == "__main__":
    asyncio.run(reset_db())
