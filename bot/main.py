"""StarsPay Bot — Main entry point."""
import logging
import asyncio
import sys
import os
import threading
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


def run_api_server():
    """Run Flask API server in a separate thread."""
    app = create_api_app()
    port = int(os.getenv("PORT", config.api_port))  # Render uses PORT env var
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


async def main():
    """Run bot and API server."""
    if not config.is_configured:
        logger.error("BOT_TOKEN not set! Set BOT_TOKEN environment variable.")
        sys.exit(1)

    # Initialize database
    await db.init()
    logger.info("Database initialized")

    # Start API server in background thread
    api_thread = threading.Thread(target=run_api_server, daemon=True)
    api_thread.start()
    api_port = int(os.getenv("PORT", config.api_port))
    logger.info(f"API server starting on port {api_port}")

    # Give API server time to start
    await asyncio.sleep(1)

    # Create bot
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # Create dispatcher
    dp = Dispatcher()
    dp.include_router(router)

    # Start bot
    logger.info("Starting StarsPay Bot polling...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
