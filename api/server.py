"""StarsPay REST API — License verification for external projects."""
import json
import time
import logging
from flask import Flask, request, jsonify
from bot.config import config
from bot.database import db

logger = logging.getLogger(__name__)


def create_api_app() -> Flask:
    """Create and configure Flask API application."""
    app = Flask(__name__)

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

        result = asyncio_run(db.verify_license(license_key))

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

        result = asyncio_run(db.check_user_license(int(user_id), project))

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


def asyncio_run(coro):
    """Run async coroutine from sync context."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result(timeout=10)
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)
