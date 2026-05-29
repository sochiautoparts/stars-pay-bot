"""Error handling middleware for StarsPay Bot."""
import logging
import asyncio
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from aiogram.exceptions import TelegramBadRequest

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(BaseMiddleware):
    """Catch and log errors without crashing the bot."""

    async def __call__(self, handler, event: TelegramObject, data: dict):
        try:
            return await handler(event, data)
        except (SystemExit, KeyboardInterrupt):
            raise  # Don't catch system exits
        except TelegramBadRequest as e:
            # Old callback queries, just ignore
            if "query is too old" in str(e) or "query ID is invalid" in str(e):
                logger.debug(f"Ignoring old callback query: {e}")
                return None
            logger.error(f"TelegramBadRequest: {e}")
        except asyncio.CancelledError:
            raise  # Don't catch cancellation
        except Exception as e:
            logger.error(f"Unhandled error: {e}", exc_info=True)
        return None
