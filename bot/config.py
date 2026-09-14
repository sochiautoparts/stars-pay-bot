"""StarsPay Bot Configuration."""
import os
import json
import logging

logger = logging.getLogger(__name__)

DEFAULT_MINIAPP_URL = "https://sochiautoparts.github.io/stars-pay-bot/"


def _env_str(name: str, default: str) -> str:
    """Read a string env var; empty/placeholder values fall back to the default."""
    v = os.getenv(name)
    if v is None:
        return default
    v = v.strip()
    if v.lower() in ("", "not_configured", "none", "null"):
        return default
    return v


def _env_int(name: str, default: int) -> int:
    """Read an int env var; empty/garbage values fall back to the default."""
    v = _env_str(name, str(default))
    try:
        return int(v)
    except ValueError:
        logger.warning(f"{name}={v!r} is not a valid integer — using default {default}")
        return default


class Config:
    """Bot configuration loaded from environment variables."""

    def __init__(self):
        # Required: must be set via environment variables
        self.bot_token = os.getenv("BOT_TOKEN", "")
        admin_ids_str = os.getenv("ADMIN_IDS", "")
        if not admin_ids_str.strip():
            logger.warning("ADMIN_IDS not set — admin commands will be unavailable")
            self.admin_ids = []
        else:
            self.admin_ids = [int(x) for x in admin_ids_str.split(",") if x.strip().isdigit()]

        self.api_port = _env_int("PORT", _env_int("API_PORT", 8080))
        api_keys_str = os.getenv("API_KEYS", "")
        if not api_keys_str:
            logger.warning("API_KEYS not set — API endpoints will reject all requests")
            self.api_keys = []
        else:
            self.api_keys = [k.strip() for k in api_keys_str.split(",") if k.strip()]

        self.database_path = _env_str("DATABASE_PATH", "starspay.db")
        self.miniapp_url = _env_str("MINIAPP_URL", DEFAULT_MINIAPP_URL)
        self.referral_bonus_stars = _env_int("REFERRAL_BONUS_STARS", 50)
        self.products = self._load_products()

    def _load_products(self) -> dict:
        """Load products from env or defaults."""
        products_str = os.getenv("PRODUCTS", "")
        if products_str:
            try:
                return json.loads(products_str)
            except json.JSONDecodeError:
                logger.error("PRODUCTS env var is not valid JSON")

        # Default product catalog
        return {
            "gitmoji-ai": {
                "name": "GitMoji AI Pro",
                "description": "Полная версия GitMoji AI с ИИ-подсказками и автокоммитами",
                "plans": {
                    "month": {"price": 149, "label": "1 месяц", "days": 30},
                    "year": {"price": 999, "label": "1 год", "days": 365},
                    "lifetime": {"price": 2999, "label": "Навсегда", "days": 0},
                },
                "prefix": "GMA",
            },
            "devbadge": {
                "name": "DevBadge Pro",
                "description": "Динамические SVG-бейджи для GitHub — анимации, кастомные темы, без водяного знака",
                "plans": {
                    "month": {"price": 149, "label": "1 месяц", "days": 30},
                    "year": {"price": 999, "label": "1 год", "days": 365},
                    "lifetime": {"price": 2999, "label": "Навсегда", "days": 0},
                },
                "prefix": "DVB",
            },
            "repokit": {
                "name": "RepoKit Pro",
                "description": "30+ шаблонов проектов: Next.js, FastAPI, Go, Rust, Flutter... CI/CD, Docker, тесты — всё включено",
                "plans": {
                    "month": {"price": 149, "label": "1 месяц", "days": 30},
                    "year": {"price": 999, "label": "1 год", "days": 365},
                    "lifetime": {"price": 2999, "label": "Навсегда", "days": 0},
                },
                "prefix": "RPK",
            },
        }

    @property
    def is_configured(self) -> bool:
        return bool(self.bot_token) and bool(self.admin_ids)


config = Config()
