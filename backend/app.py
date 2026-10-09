"""Flask application factory for SafeRoute AI."""
import logging
import os
import sys
import time

from flask import Flask, g, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException

_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

from backend.api.routes import api_bp  # noqa: E402
from backend.config import Config  # noqa: E402
from backend.storage import db  # noqa: E402

_FRONTEND_DIST = os.path.join(_ROOT_DIR, "frontend", "dist")


def create_app(config=Config):
    app = Flask(__name__)
    app.config.from_object(config)

    db_path = app.config.get("SQLITE_PATH", Config.SQLITE_PATH)
    if db_path and db_path != ":memory:":
        manifest = os.path.join(app.config.get("IMAGE_DIR", Config.IMAGE_DIR), "manifest.json")
        db.init_db(db_path, image_manifest=manifest)
        db.purge_expired_query_logs(
            db_path, app.config.get("LOG_RETENTION_DAYS", Config.LOG_RETENTION_DAYS)
        )

    app.register_blueprint(api_bp)
    logging.basicConfig(level=logging.INFO)

    @app.before_request
    def _start_timer():
        g._start = time.perf_counter()

    @app.after_request
    def _log_latency(response):
        if hasattr(g, "_start"):
            elapsed = (time.perf_counter() - g._start) * 1000
            logging.getLogger("saferoute").info(
                "%s %s -> %s (%.0f ms)", request.method, request.path, response.status_code, elapsed
            )
        return response

    @app.errorhandler(HTTPException)
    def _http_error(exc):
        if request.path.startswith("/api"):
            return jsonify({"error": exc.name, "detail": exc.description}), exc.code
        return exc

    @app.errorhandler(Exception)
    def _server_error(exc):
        if isinstance(exc, HTTPException):
            return exc
        logging.getLogger("saferoute").exception("unhandled error")
        return jsonify({"error": "internal server error", "detail": str(exc)}), 500

    @app.route("/")
    def index():
        return send_from_directory(_FRONTEND_DIST, "index.html")

    @app.route("/<path:path>")
    def static_files(path):
        if path.startswith("api/"):
            return jsonify({"error": "not found"}), 404
        if os.path.isfile(os.path.join(_FRONTEND_DIST, path)):
            return send_from_directory(_FRONTEND_DIST, path)
        # SPA fallback: unknown non-API paths serve the React entry point.
        return send_from_directory(_FRONTEND_DIST, "index.html")

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000, debug=True)
