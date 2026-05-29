"""StarsPay REST API — License verification for external projects."""
import json
import time
import asyncio
import logging
import sqlite3
from flask import Flask, request, jsonify
from bot.config import config
from bot.database import db

logger = logging.getLogger(__name__)

# Track if DB is initialized
_db_initialized = False


def _ensure_db():
    """Ensure database is initialized (sync version for Flask)."""
    global _db_initialized
    if _db_initialized:
        return
    try:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(db.init())
        loop.close()
        _db_initialized = True
        logger.info("Database initialized for API server")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")


def _sync_verify_license(key: str) -> dict:
    """Verify a license key using sync sqlite3 (for Flask)."""
    _ensure_db()
    try:
        conn = sqlite3.connect(config.database_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT * FROM licenses WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return {"valid": False, "reason": "key_not_found"}

        license_data = dict(row)
        if not license_data["active"]:
            return {"valid": False, "reason": "deactivated"}

        # Check expiration (0 = lifetime)
        if license_data["expires_at"] > 0 and time.time() > license_data["expires_at"]:
            conn = sqlite3.connect(config.database_path)
            conn.execute("UPDATE licenses SET active = 0 WHERE key = ?", (key,))
            conn.commit()
            conn.close()
            return {"valid": False, "reason": "expired"}

        return {"valid": True, "license": license_data}
    except Exception as e:
        logger.error(f"License verification error: {e}")
        return {"valid": False, "reason": "error"}


def _sync_check_user_license(user_id: int, project: str) -> dict:
    """Check if user has active license (sync sqlite3 for Flask)."""
    _ensure_db()
    try:
        conn = sqlite3.connect(config.database_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM licenses WHERE user_id = ? AND project = ? AND active = 1",
            (user_id, project)
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return {"has_license": False}

        license_data = dict(row)
        if license_data["expires_at"] > 0 and time.time() > license_data["expires_at"]:
            conn = sqlite3.connect(config.database_path)
            conn.execute(
                "UPDATE licenses SET active = 0 WHERE user_id = ? AND project = ?",
                (user_id, project)
            )
            conn.commit()
            conn.close()
            return {"has_license": False, "reason": "expired"}

        return {"has_license": True, "license": license_data}
    except Exception as e:
        logger.error(f"User license check error: {e}")
        return {"has_license": False, "reason": "error"}


def create_api_app() -> Flask:
    """Create and configure Flask API application."""
    app = Flask(__name__)

    # Initialize DB on first request
    @app.before_request
    def init_db():
        _ensure_db()

    @app.route("/api/v1/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok", "service": "starspay", "version": "1.0.0"})

    @app.route("/api/v1/verify", methods=["POST"])
    def verify_license():
        """Verify a license key.
        Headers: X-API-Key: <api_key>
        Body: {"key": "SP-GMA-XXXX-XXXX"}
        """
        api_key = request.headers.get("X-API-Key", "")
        if api_key not in config.api_keys:
            return jsonify({"error": "invalid_api_key"}), 401

        data = request.get_json(silent=True) or {}
        license_key = data.get("key", "").strip()

        if not license_key:
            return jsonify({"error": "missing_key"}), 400

        result = _sync_verify_license(license_key)

        if result["valid"]:
            lic = result["license"]
            return jsonify({
                "valid": True,
                "project": lic["project"],
                "plan": lic["plan"],
                "expires_at": lic["expires_at"],
                "is_lifetime": lic["expires_at"] == 0,
            })
        else:
            return jsonify({"valid": False, "reason": result.get("reason", "unknown")})

    @app.route("/api/v1/check", methods=["POST"])
    def check_user():
        """Check if a user has active license.
        Headers: X-API-Key: <api_key>
        Body: {"user_id": 12345, "project": "gitmoji-ai"}
        """
        api_key = request.headers.get("X-API-Key", "")
        if api_key not in config.api_keys:
            return jsonify({"error": "invalid_api_key"}), 401

        data = request.get_json(silent=True) or {}
        user_id = data.get("user_id")
        project = data.get("project", "")

        if not user_id:
            return jsonify({"error": "missing_user_id"}), 400

        result = _sync_check_user_license(int(user_id), project)

        if result.get("has_license"):
            lic = result["license"]
            return jsonify({
                "has_license": True,
                "project": lic["project"],
                "plan": lic["plan"],
                "expires_at": lic["expires_at"],
                "is_lifetime": lic["expires_at"] == 0,
            })
        else:
            return jsonify({"has_license": False, "reason": result.get("reason", "no_license")})

    @app.route("/api/v1/projects", methods=["GET"])
    def list_projects():
        """List available projects (public endpoint)."""
        projects = {}
        for pid, pdata in config.products.items():
            projects[pid] = {
                "name": pdata["name"],
                "description": pdata["description"],
                "plans": {
                    k: {"price": v["price"], "label": v["label"], "days": v["days"]}
                    for k, v in pdata["plans"].items()
                }
            }
        return jsonify({"projects": projects})

    return app
