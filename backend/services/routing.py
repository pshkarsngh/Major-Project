"""Google Maps geocoding + Directions (spec FR-001, FR-002; research R1)."""
import requests

from ..config import Config
from .errors import LocationError, UpstreamError

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
DIRECTIONS_URL = "https://maps.googleapis.com/maps/api/directions/json"
_TIMEOUT = 10


def decode_polyline(encoded):
    """Decode a Google encoded polyline into [(lat, lng), ...]."""
    points = []
    index = lat = lng = 0
    while index < len(encoded):
        for is_lng in (False, True):
            shift = result = 0
            while True:
                byte = ord(encoded[index]) - 63
                index += 1
                result |= (byte & 0x1F) << shift
                shift += 5
                if byte < 0x20:
                    break
            delta = ~(result >> 1) if (result & 1) else (result >> 1)
            if is_lng:
                lng += delta
            else:
                lat += delta
        points.append((lat / 1e5, lng / 1e5))
    return points


def geocode(address, api_key=None):
    api_key = api_key or Config.GOOGLE_MAPS_API_KEY
    if not address or not address.strip():
        raise LocationError("empty address")
    if not api_key:
        raise UpstreamError("GOOGLE_MAPS_API_KEY is not configured")
    try:
        resp = requests.get(
            GEOCODE_URL, params={"address": address, "key": api_key}, timeout=_TIMEOUT
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        raise UpstreamError(f"geocoding failed: {exc}") from exc
    if data.get("status") != "OK" or not data.get("results"):
        raise LocationError(f"could not resolve location: {address}")
    result = data["results"][0]
    loc = result["geometry"]["location"]
    return {
        "lat": loc["lat"],
        "lng": loc["lng"],
        "formatted_address": result.get("formatted_address", address),
    }


def get_routes(origin, destination, api_key=None):
    """Return candidate routes with distance/duration and decoded polyline points."""
    api_key = api_key or Config.GOOGLE_MAPS_API_KEY
    if not api_key:
        raise UpstreamError("GOOGLE_MAPS_API_KEY is not configured")
    params = {
        "origin": f"{origin['lat']},{origin['lng']}",
        "destination": f"{destination['lat']},{destination['lng']}",
        "alternatives": "true",
        "key": api_key,
    }
    try:
        resp = requests.get(DIRECTIONS_URL, params=params, timeout=_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        raise UpstreamError(f"directions failed: {exc}") from exc
    if data.get("status") != "OK" or not data.get("routes"):
        raise UpstreamError(f"no routes returned: {data.get('status')}")

    routes = []
    for i, route in enumerate(data["routes"]):
        leg = route["legs"][0]
        points = decode_polyline(route["overview_polyline"]["points"])
        routes.append(
            {
                "id": f"r{i + 1}",
                "distance_m": int(leg["distance"]["value"]),
                "duration_s": int(leg["duration"]["value"]),
                "polyline": route["overview_polyline"]["points"],
                "points": points,
            }
        )
    return routes
