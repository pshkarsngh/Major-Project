"""Split a route polyline into approximately equal-length segments (spec FR-003)."""
import math

_EARTH_RADIUS_M = 6371000.0


def _haversine(a, b):
    lat1, lng1 = a
    lat2, lng2 = b
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    h = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * _EARTH_RADIUS_M * math.asin(math.sqrt(h))


def _make_segment(start, end):
    mid = ((start[0] + end[0]) / 2.0, (start[1] + end[1]) / 2.0)
    return {
        "start_lat": start[0],
        "start_lng": start[1],
        "end_lat": end[0],
        "end_lng": end[1],
        "midpoint_lat": mid[0],
        "midpoint_lng": mid[1],
        "length_m": _haversine(start, end),
    }


def segment_route(points, target_length_m=300.0):
    """Return segments of ~target_length_m along the polyline `points` [(lat,lng)]."""
    if not points or len(points) < 2:
        return []

    segments = []
    seg_start = points[0]
    cur = points[0]
    accumulated = 0.0

    for nxt in points[1:]:
        leg = _haversine(cur, nxt)
        while accumulated + leg >= target_length_m and leg > 1e-9:
            need = target_length_m - accumulated
            frac = need / leg
            cut = (
                cur[0] + (nxt[0] - cur[0]) * frac,
                cur[1] + (nxt[1] - cur[1]) * frac,
            )
            segments.append(_make_segment(seg_start, cut))
            seg_start = cut
            cur = cut
            leg = _haversine(cur, nxt)
            accumulated = 0.0
        accumulated += leg
        cur = nxt

    if _haversine(seg_start, points[-1]) > 1e-6:
        segments.append(_make_segment(seg_start, points[-1]))
    return segments
