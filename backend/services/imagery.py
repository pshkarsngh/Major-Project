"""Segment midpoint -> nearest usable road image lookup (FR-004, FR-018)."""
import math
from datetime import datetime, timedelta, timezone

from ..config import Config
from ..storage import db

_EARTH_RADIUS_M = 6371000.0
_MAX_LOOKUP_RADIUS_M = 250.0


def haversine(lat1, lng1, lat2, lng2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * _EARTH_RADIUS_M * math.asin(math.sqrt(a))


def is_stale(image, reference=None, staleness_days=None):
    """True when the image has no usable capture time or is older than the cutoff (FR-018)."""
    staleness_days = Config.IMAGERY_STALENESS_DAYS if staleness_days is None else staleness_days
    captured = image.get("captured_at")
    if not captured:
        return True
    try:
        captured_at = datetime.fromisoformat(captured)
    except (ValueError, TypeError):
        return True
    if captured_at.tzinfo is None:
        captured_at = captured_at.replace(tzinfo=timezone.utc)
    reference = reference or datetime.now(timezone.utc)
    return (reference - captured_at) > timedelta(days=staleness_days)


def find_nearest_image(lat, lng, db_path=None, max_radius_m=_MAX_LOOKUP_RADIUS_M,
                       staleness_days=None, reference=None):
    """Return the closest non-stale road image within max_radius_m, else None."""
    db_path = db_path or Config.SQLITE_PATH
    best, best_d = None, None
    for img in db.list_images(db_path):
        if is_stale(img, reference=reference, staleness_days=staleness_days):
            continue
        d = haversine(lat, lng, img["lat"], img["lng"])
        if best_d is None or d < best_d:
            best, best_d = img, d
    if best is not None and best_d is not None and best_d <= max_radius_m:
        return best
    return None
