"""StarsPay Bot — Main entry point."""
import logging
import asyncio
import sys
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from bot.config import config
from bot.database import db
from bot.handlers import router
from api.server import create_api_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Run bot and API server."""
    if not config.is_configured:
        logger.error("BOT_TOKEN not set! Set BOT_TOKEN environment variable.")
        sys.exit(1)

    # Initialize database
    await db.init()
    logger.info("Database initialized")

    # Create bot
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # Create dispatcher
    dp = Dispatcher()
    dp.include_router(router)

    # Start API server in background
    api_app = create_api_app()
    runner = asyncio.create_task(
        asyncio.to_thread(
            lambda: api_app.run(host="0.0.0.0", port=config.api_port)
        )
    )
    logger.info(f"API server starting on port {config.api_port}")

    # Start bot
    logger.info("Starting StarsPay Bot...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
