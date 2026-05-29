"""StarsPay Bot Configuration."""
import os
import yaml


class Config:
    """Bot configuration loaded from environment or config.yaml."""

    def __init__(self):
        self.bot_token = os.getenv("BOT_TOKEN", "")
        self.admin_ids = [
            int(x) for x in os.getenv("ADMIN_IDS", "265070804").split(",") if x.strip()
        ]
        self.api_port = int(os.getenv("API_PORT", "8080"))
        self.api_keys_str = os.getenv("API_KEYS", "starspay-default-key-change-me")
        self.api_keys = [k.strip() for k in self.api_keys_str.split(",") if k.strip()]
        self.database_path = os.getenv("DATABASE_PATH", "starspay.db")
        self.miniapp_url = os.getenv(
            "MINIAPP_URL",
            "https://sochiautoparts.github.io/stars-pay-bot/"
        )
        self.referral_bonus_stars = int(os.getenv("REFERRAL_BONUS_STARS", "50"))
        self.products = self._load_products()

    def _load_products(self) -> dict:
        """Load products from env or defaults."""
        products_str = os.getenv("PRODUCTS", "")
        if products_str:
            import json
            return json.loads(products_str)

        # Default products for multiple projects
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
            "code-review": {
                "name": "Code Review Bot Pro",
                "description": "AI-ревью кода с детальными suggestions",
                "plans": {
                    "month": {"price": 99, "label": "1 месяц", "days": 30},
                    "year": {"price": 699, "label": "1 год", "days": 365},
                },
                "prefix": "CRB",
            },
            "dev-tools": {
                "name": "Dev Tools Suite",
                "description": "Набор инструментов для разработчика",
                "plans": {
                    "month": {"price": 199, "label": "1 месяц", "days": 30},
                    "lifetime": {"price": 4999, "label": "Навсегда", "days": 0},
                },
                "prefix": "DTS",
            },
        }

    @property
    def is_configured(self) -> bool:
        return bool(self.bot_token)


config = Config()
