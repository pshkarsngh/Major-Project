import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.app import create_app  # noqa: E402
from backend.config import Config  # noqa: E402


def make_routes():
    """Two candidate routes near Mangalore with different durations/geometry."""
    return [
        {
            "id": "r1",
            "distance_m": 9000,
            "duration_s": 900,
            "polyline": "",
            "points": [(12.900, 74.840), (12.905, 74.850), (12.910, 74.860)],
        },
        {
            "id": "r2",
            "distance_m": 9600,
            "duration_s": 1080,
            "polyline": "",
            "points": [(12.900, 74.840), (12.906, 74.852), (12.912, 74.858)],
        },
    ]


@pytest.fixture
def app(tmp_path):
    class Cfg(Config):
        SQLITE_PATH = str(tmp_path / "test.db")
        IMAGE_DIR = str(tmp_path / "images")
        GOOGLE_MAPS_API_KEY = ""
        LLM_API_KEY = ""

    os.makedirs(Cfg.IMAGE_DIR, exist_ok=True)
    application = create_app(Cfg)
    application.config["TESTING"] = True
    return application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def mock_services(monkeypatch):
    """Mock routing (and make LLM a no-op) at the routes boundary."""
    from backend.api import routes

    monkeypatch.setattr(
        routes.routing,
        "geocode",
        lambda address, **kwargs: {"lat": 12.9, "lng": 74.85, "formatted_address": address},
    )
    monkeypatch.setattr(routes.routing, "get_routes", lambda o, d, **kwargs: make_routes())
    return routes
