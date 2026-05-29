"""StarsPay Database — SQLite with multi-project support."""
import aiosqlite
import uuid
import time
from bot.config import config


class Database:
    """Async SQLite database for StarsPay."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.database_path

    async def init(self):
        """Initialize database tables."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    language_code TEXT DEFAULT 'ru',
                    referred_by INTEGER,
                    referral_code TEXT UNIQUE,
                    stars_balance INTEGER DEFAULT 0,
                    created_at REAL
                );

                CREATE TABLE IF NOT EXISTS licenses (
                    key TEXT PRIMARY KEY,
                    user_id INTEGER,
                    project TEXT NOT NULL,
                    plan TEXT NOT NULL,
                    activated_at REAL,
                    expires_at REAL,
                    active INTEGER DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                );

                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    project TEXT,
                    plan TEXT,
                    stars_amount INTEGER,
                    telegram_charge_id TEXT,
                    provider_charge_id TEXT,
                    license_key TEXT,
                    created_at REAL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                );

                CREATE TABLE IF NOT EXISTS api_keys (
                    key TEXT PRIMARY KEY,
                    project TEXT NOT NULL,
                    description TEXT,
                    created_at REAL
                );

                CREATE TABLE IF NOT EXISTS referrals (
                    referrer_id INTEGER,
                    referred_id INTEGER,
                    bonus_given INTEGER DEFAULT 0,
                    created_at REAL,
                    PRIMARY KEY (referrer_id, referred_id)
                );

                CREATE INDEX IF NOT EXISTS idx_licenses_user ON licenses(user_id);
                CREATE INDEX IF NOT EXISTS idx_licenses_project ON licenses(project);
                CREATE INDEX IF NOT EXISTS idx_licenses_active ON licenses(active);
                CREATE INDEX IF NOT EXISTS idx_payments_user ON payments(user_id);
            """)
            await db.commit()

    async def get_or_create_user(self, user_id: int, username: str = None,
                                  first_name: str = None, lang: str = "ru") -> dict:
        """Get or create a user, returning user data."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            if row:
                # Update username/name if changed
                if username or first_name:
                    await db.execute(
                        "UPDATE users SET username = ?, first_name = ? WHERE user_id = ?",
                        (username, first_name, user_id)
                    )
                    await db.commit()
                return dict(row)

            ref_code = uuid.uuid4().hex[:8].upper()
            await db.execute(
                """INSERT INTO users (user_id, username, first_name, language_code, referral_code, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (user_id, username, first_name, lang, ref_code, time.time())
            )
            await db.commit()
            cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            return dict(await cursor.fetchone())

    async def generate_license_key(self, project_prefix: str) -> str:
        """Generate a unique license key like SP-GMA-A1B2-C3D4."""
        while True:
            part1 = uuid.uuid4().hex[:4].upper()
            part2 = uuid.uuid4().hex[:4].upper()
            key = f"SP-{project_prefix}-{part1}-{part2}"
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("SELECT 1 FROM licenses WHERE key = ?", (key,))
                if not await cursor.fetchone():
                    return key

    async def create_license(self, user_id: int, project: str, plan: str,
                              expires_at: float = 0) -> str:
        """Create a new license key."""
        products = config.products
        product = products.get(project, {})
        prefix = product.get("prefix", "GEN")

        key = await self.generate_license_key(prefix)
        now = time.time()

        async with aiosqlite.connect(self.db_path) as db:
            # Deactivate old licenses for same user+project
            await db.execute(
                "UPDATE licenses SET active = 0 WHERE user_id = ? AND project = ? AND active = 1",
                (user_id, project)
            )
            await db.execute(
                """INSERT INTO licenses (key, user_id, project, plan, activated_at, expires_at, active)
                   VALUES (?, ?, ?, ?, ?, ?, 1)""",
                (key, user_id, project, plan, now, expires_at, )
            )
            await db.commit()
        return key

    async def verify_license(self, key: str) -> dict:
        """Verify a license key. Returns license info or None."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM licenses WHERE key = ?", (key,))
            row = await cursor.fetchone()
            if not row:
                return {"valid": False, "reason": "key_not_found"}

            license_data = dict(row)
            if not license_data["active"]:
                return {"valid": False, "reason": "deactivated"}

            # Check expiration (0 = lifetime)
            if license_data["expires_at"] > 0 and time.time() > license_data["expires_at"]:
                async with aiosqlite.connect(self.db_path) as db2:
                    await db2.execute("UPDATE licenses SET active = 0 WHERE key = ?", (key,))
                    await db2.commit()
                return {"valid": False, "reason": "expired"}

            return {"valid": True, "license": license_data}

    async def check_user_license(self, user_id: int, project: str) -> dict:
        """Check if user has an active license for a project."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM licenses WHERE user_id = ? AND project = ? AND active = 1",
                (user_id, project)
            )
            row = await cursor.fetchone()
            if not row:
                return {"has_license": False}

            license_data = dict(row)
            if license_data["expires_at"] > 0 and time.time() > license_data["expires_at"]:
                async with aiosqlite.connect(self.db_path) as db2:
                    await db2.execute(
                        "UPDATE licenses SET active = 0 WHERE user_id = ? AND project = ?",
                        (user_id, project)
                    )
                    await db2.commit()
                return {"has_license": False, "reason": "expired"}

            return {"has_license": True, "license": license_data}

    async def record_payment(self, user_id: int, project: str, plan: str,
                              stars: int, tg_charge_id: str, provider_charge_id: str,
                              license_key: str):
        """Record a successful payment."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO payments (user_id, project, plan, stars_amount,
                   telegram_charge_id, provider_charge_id, license_key, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, project, plan, stars, tg_charge_id, provider_charge_id,
                 license_key, time.time())
            )
            await db.commit()

    async def set_referral(self, referrer_id: int, referred_id: int):
        """Record a referral relationship."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT OR IGNORE INTO referrals (referrer_id, referred_id, bonus_given, created_at)
                   VALUES (?, ?, 0, ?)""",
                (referrer_id, referred_id, time.time())
            )
            # Update user's referrer
            await db.execute(
                "UPDATE users SET referred_by = ? WHERE user_id = ? AND referred_by IS NULL",
                (referrer_id, referred_id)
            )
            await db.commit()

    async def get_user_stats(self, user_id: int) -> dict:
        """Get user statistics."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            # Count referrals
            cursor = await db.execute(
                "SELECT COUNT(*) as cnt FROM referrals WHERE referrer_id = ?", (user_id,)
            )
            ref_count = (await cursor.fetchone())["cnt"]

            # Get active licenses
            cursor = await db.execute(
                "SELECT project, plan, expires_at FROM licenses WHERE user_id = ? AND active = 1",
                (user_id,)
            )
            licenses = [dict(r) for r in await cursor.fetchall()]

            # Get total spent
            cursor = await db.execute(
                "SELECT COALESCE(SUM(stars_amount), 0) as total FROM payments WHERE user_id = ?",
                (user_id,)
            )
            total_spent = (await cursor.fetchone())["total"]

            return {
                "referrals": ref_count,
                "licenses": licenses,
                "total_spent": total_spent,
            }

    async def get_admin_stats(self) -> dict:
        """Get admin statistics."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            cursor = await db.execute("SELECT COUNT(*) as cnt FROM users")
            total_users = (await cursor.fetchone())["cnt"]

            cursor = await db.execute("SELECT COUNT(*) as cnt FROM licenses WHERE active = 1")
            active_licenses = (await cursor.fetchone())["cnt"]

            cursor = await db.execute("SELECT COALESCE(SUM(stars_amount), 0) as total FROM payments")
            total_stars = (await cursor.fetchone())["total"]

            cursor = await db.execute(
                "SELECT project, COUNT(*) as cnt FROM licenses WHERE active = 1 GROUP BY project"
            )
            by_project = {dict(r)["project"]: dict(r)["cnt"] for r in await cursor.fetchall()}

            return {
                "total_users": total_users,
                "active_licenses": active_licenses,
                "total_stars": total_stars,
                "by_project": by_project,
            }

    async def add_api_key(self, key: str, project: str, description: str = ""):
        """Add an API key for external project access."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO api_keys (key, project, description, created_at) VALUES (?, ?, ?, ?)",
                (key, project, description, time.time())
            )
            await db.commit()

    async def verify_api_key(self, key: str) -> dict:
        """Verify an API key and return project info."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM api_keys WHERE key = ?", (key,))
            row = await cursor.fetchone()
            if row:
                return {"valid": True, "project": dict(row)}
            return {"valid": False}


# Global database instance
db = Database()
