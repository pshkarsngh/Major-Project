"""Request/response validation helpers (no external dependency)."""
from ..config import Config


def validate_route_request(data):
    """Return (cleaned, error_message). error_message is None when valid."""
    if not isinstance(data, dict):
        return None, "request body must be a JSON object"
    origin = data.get("origin")
    destination = data.get("destination")
    if not isinstance(origin, str) or not origin.strip():
        return None, "origin is required"
    if not isinstance(destination, str) or not destination.strip():
        return None, "destination is required"
    preference = data.get("preference")
    if preference is not None and not isinstance(preference, str):
        return None, "preference must be a string"
    return {
        "origin": origin.strip()[:512],
        "destination": destination.strip()[:512],
        "preference": (preference or "").strip()[:1000],
    }, None


def clamp_score(value):
    try:
        return max(0.0, min(100.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def clamp_alpha(value):
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.5


def valid_avoid_classes(values):
    if not values:
        return []
    return [v for v in values if v in Config.HAZARD_CLASSES]
