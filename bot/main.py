"""StarsPay Bot — Main entry point."""
import logging
import asyncio
import sys
import os
import signal
import threading
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from bot.config import config
from bot.database import db
from bot.handlers import router
from bot.middleware import ErrorHandlingMiddleware

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

    # Start API server in background thread
    from api.server import create_api_app
    api_app = create_api_app()
    api_thread = threading.Thread(
        target=lambda: api_app.run(host="0.0.0.0", port=config.api_port, debug=False, use_reloader=False),
        daemon=True
    )
    api_thread.start()
    logger.info(f"API server starting on port {config.api_port}")

    await asyncio.sleep(1)

    # Create bot
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # Create dispatcher
    dp = Dispatcher()
    dp.include_router(router)

    # Add error handling middleware
    dp.message.middleware(ErrorHandlingMiddleware())
    dp.callback_query.middleware(ErrorHandlingMiddleware())
    dp.pre_checkout_query.middleware(ErrorHandlingMiddleware())

    # Auto-stop after configured time (for GitHub Actions burst mode)
    run_seconds = int(os.getenv("BOT_RUN_SECONDS", "0"))
    if run_seconds > 0:
        async def auto_stop():
            await asyncio.sleep(run_seconds)
            logger.info(f"Auto-stop after {run_seconds}s (BOT_RUN_SECONDS)")
            # Gracefully stop polling
            raise SystemExit(0)
        asyncio.create_task(auto_stop())

    # Start bot
    logger.info("Starting StarsPay Bot polling...")
    try:
        await dp.start_polling(bot)
    except (SystemExit, KeyboardInterrupt):
        logger.info("Bot stopping...")
    finally:
        await bot.session.close()
        logger.info("Bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (SystemExit, KeyboardInterrupt):
        pass
