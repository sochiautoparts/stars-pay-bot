"""StarsPay REST API — License verification for external projects."""
import json
import time
import hashlib
import sqlite3
import logging
import os
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
        import asyncio
        loop = asyncio.new_event_loop()
        loop.run_until_complete(db.init())
        loop.close()
        _db_initialized = True
        logger.info("Database initialized for API server")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")


def _sync_verify_license(key: str) -> dict:
    """Verify a license key using sync sqlite3."""
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
    """Check if user has active license (sync sqlite3)."""
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


def _verify_from_json(key: str) -> dict:
    """Verify a license key using the public licenses.json file."""
    json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "licenses.json")
    try:
        with open(json_path, "r") as f:
            data = json.load(f)

        key_hash = hashlib.sha256(key.encode()).hexdigest()[:16]

        for lic in data.get("licenses", []):
            if lic.get("key_hash") == key_hash and lic.get("active"):
                # Check expiration
                if lic.get("expires_at", 0) > 0 and time.time() > lic["expires_at"]:
                    return {"valid": False, "reason": "expired"}
                return {
                    "valid": True,
                    "project": lic.get("project"),
                    "plan": lic.get("plan"),
                    "expires_at": lic.get("expires_at", 0),
                    "is_lifetime": lic.get("expires_at", 0) == 0,
                }

        return {"valid": False, "reason": "key_not_found"}
    except FileNotFoundError:
        logger.warning("licenses.json not found, falling back to database")
        return _sync_verify_license(key)
    except Exception as e:
        logger.error(f"JSON verification error: {e}")
        return {"valid": False, "reason": "error"}


def create_api_app() -> Flask:
    """Create and configure Flask API application."""
    app = Flask(__name__)

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

        # Try database first, then JSON fallback
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
            # Try JSON file (for cases where DB is empty but JSON has data)
            json_result = _verify_from_json(license_key)
            if json_result["valid"]:
                return jsonify(json_result)
            return jsonify({"valid": False, "reason": result.get("reason", "unknown")})

    @app.route("/api/v1/check", methods=["POST"])
    def check_user():
        """Check if a user has active license."""
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
