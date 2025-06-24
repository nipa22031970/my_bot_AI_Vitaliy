import sys
import asyncio
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from src.db.initializator import DatabaseInitializer
from src.db.repository import GptSessionRepository
from src.bot.environment import EnvironmentMiddleware
from src.bot.commands import router as commands_router
from services.chatgpt.open_ai_client import OpenAIClient
from settings.config import config
from settings.logging_config import get_logger

BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

logger = get_logger(__name__)


def setup_dependencies():
    db_initializator = DatabaseInitializer(config.path_to_db)
    db_initializator.create_tables()
    session_repository = GptSessionRepository(config.path_to_db)
    openai_client = OpenAIClient(
        openai_api_key=config.openai_api_token,
        model=config.opeanai_model,
        temperature=config.opeanai_model_temperature
    )
    return session_repository, openai_client


async def main():
    session_repository, openai_client = setup_dependencies()
    bot = Bot(
        token=config.telegram_bot_api_key,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.message.middleware(
        EnvironmentMiddleware(
            openai_client=openai_client,
            session_repository=session_repository
        )
    )
    dp.include_router(commands_router)
    logger.info("Bot is starting...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.exception(f"Bot crashed: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.exception(f"Failed to start bot: {e}")
