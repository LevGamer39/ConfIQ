import asyncio
import sqlite3
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, BOT_CONFIG
from database import FDataBase
from services.gigachat_service import GigaChatService
from services.parser_service import ParserService
from handlers.user_handlers import router as user_router
from handlers.admin_handlers import router as admin_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

OWNER_ID = BOT_CONFIG['admin_ids'][0] if BOT_CONFIG['admin_ids'] else 0

async def main():
    logger.info("🚀 Starting AI Media Agent Sber...")
    
    try:
        conn = sqlite3.connect('sber_events.db', check_same_thread=False)
        conn.row_factory = sqlite3.Row
        db = FDataBase(conn)
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return

    try:
        if OWNER_ID != 0:
            admin_data = db.get_admin(OWNER_ID)
            if not admin_data:
                db.add_admin(OWNER_ID, "Owner", "GreatAdmin")
                logger.info(f"✅ Owner {OWNER_ID} added as GreatAdmin")
            elif admin_data.get('role') != 'GreatAdmin':
                db.remove_admin(OWNER_ID)
                db.add_admin(OWNER_ID, "Owner", "GreatAdmin")
                logger.info(f"✅ Owner {OWNER_ID} rights confirmed as GreatAdmin")
                
            user_data = db.get_user(OWNER_ID)
            if not user_data:
                db.add_user(OWNER_ID, "Owner", "Owner")
                db.force_approve_user(OWNER_ID)
                logger.info(f"✅ Owner {OWNER_ID} auto-registered and approved as user")
            elif user_data.get('status') != 'approved':
                db.force_approve_user(OWNER_ID)
                logger.info(f"✅ Owner {OWNER_ID} auto-approved as user")
                
    except Exception as e:
        logger.error(f"❌ Owner setup error: {e}")

    try:
        gigachat = GigaChatService()
        parser = ParserService()
        logger.info("✅ Services initialized successfully")
    except Exception as e:
        logger.error(f"❌ Services initialization failed: {e}")
        return

    try:
        bot = Bot(token=BOT_TOKEN)
        dp = Dispatcher(storage=MemoryStorage())
        logger.info("✅ Bot initialized successfully")
    except Exception as e:
        logger.error(f"❌ Bot initialization failed: {e}")
        return

    dp["db"] = db
    dp["gigachat"] = gigachat
    dp["parser"] = parser

    dp.include_router(admin_router)
    dp.include_router(user_router)

    logger.info("🤖 AI Media Agent Sber is ready! Starting polling...")
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"❌ Polling error: {e}")
    finally:
        await bot.session.close()
        conn.close()
        logger.info("👋 Bot stopped")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")