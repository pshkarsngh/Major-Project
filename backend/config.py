"""Environment-driven configuration for SafeRoute AI.

Prototype constants (safety weights, decay factor) are relative-risk values,
not validated against accident data. See specs/001-safe-route-navigation/research.md.
"""
import os

_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR = os.path.dirname(_BACKEND_DIR)


def _float(name, default):
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return float(default)


class Config:
    GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
    LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-4o-mini")
    LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")

    SAFETY_DECAY_LAMBDA = _float("SAFETY_DECAY_LAMBDA", 0.15)
    DETECTION_CONFIDENCE_THRESHOLD = _float("DETECTION_CONFIDENCE_THRESHOLD", 0.4)
    SEGMENT_LENGTH_M = _float("SEGMENT_LENGTH_M", 300)
    IMAGERY_STALENESS_DAYS = _float("IMAGERY_STALENESS_DAYS", 180)
    LOG_RETENTION_DAYS = _float("LOG_RETENTION_DAYS", 30)

    SQLITE_PATH = os.environ.get("SQLITE_PATH", os.path.join(_BACKEND_DIR, "saferoute.db"))
    IMAGE_DIR = os.environ.get("IMAGE_DIR", os.path.join(_BACKEND_DIR, "data", "images"))
    YOLO_WEIGHTS = os.environ.get("YOLO_WEIGHTS", os.path.join(_ROOT_DIR, "ml", "weights", "best.pt"))

    # gamma_c: relative penalty per hazard class.
    CLASS_WEIGHTS = {
        "pothole": 3.0,
        "crack": 1.5,
        "damaged_patch": 2.0,
        "waterlogging": 2.5,
        "uneven_surface": 1.5,
    }
    SEVERITY_WEIGHTS = {"low": 1, "medium": 2, "high": 3}
    HAZARD_CLASSES = tuple(CLASS_WEIGHTS.keys())
