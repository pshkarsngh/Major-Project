"""REST API: /api/health, /api/route, /api/hazards (contracts/openapi.yaml)."""
import json
import os

from flask import Blueprint, current_app, jsonify, request

from ..config import Config
from ..services import imagery, llm, routing, scoring, segmentation, vision
from ..services.errors import LocationError, UpstreamError
from ..storage import db
from . import schemas

api_bp = Blueprint("api", __name__, url_prefix="/api")


def _config(key, default):
    return current_app.config.get(key, default)


def _db_path():
    return _config("SQLITE_PATH", Config.SQLITE_PATH)


def _error(message, status, detail=None):
    return jsonify({"error": message, "detail": detail}), status


def _resolve_image_path(file_path):
    if not file_path:
        return file_path
    if os.path.isabs(file_path):
        return file_path
    return os.path.join(_config("IMAGE_DIR", Config.IMAGE_DIR), file_path)


def _cached_to_detections(rows):
    detections = []
    for row in rows:
        severity = row.get("severity", "low")
        detections.append(
            {
                "hazard_class": row["hazard_class"],
                "confidence": row["confidence"],
                "severity": severity,
                "severity_weight": Config.SEVERITY_WEIGHTS.get(severity, 1),
                "class_weight": row.get("class_weight", 1.0),
            }
        )
    return detections


def _assess_route(route, class_weights, db_path):
    segments = segmentation.segment_route(
        route["points"], _config("SEGMENT_LENGTH_M", Config.SEGMENT_LENGTH_M)
    )
    segment_costs = []
    assessed_count = 0
    hazards = []
    summary = {}

    for idx, seg in enumerate(segments):
        image = imagery.find_nearest_image(
            seg["midpoint_lat"], seg["midpoint_lng"], db_path=db_path
        )
        if not image:
            continue  # unassessed (missing/stale) -> excluded from the average (FR-019)
        cached = db.get_cached_detections(db_path, image["id"])
        detections = (
            _cached_to_detections(cached)
            if cached
            else vision.detect(
                _resolve_image_path(image["file_path"]), class_weights=class_weights
            )
        )
        if detections and not cached:
            db.save_detections(db_path, image["id"], idx, detections)

        assessed_count += 1
        segment_costs.append(scoring.segment_hazard_cost(detections, class_weights))
        for det in detections:
            hazards.append(
                {
                    "class": det["hazard_class"],
                    "confidence": round(float(det["confidence"]), 3),
                    "severity": det.get("severity", "low"),
                    "lat": seg["midpoint_lat"],
                    "lng": seg["midpoint_lng"],
                }
            )
            summary[det["hazard_class"]] = summary.get(det["hazard_class"], 0) + 1

    hazard_cost = scoring.route_hazard_cost(segment_costs)
    return {
        "id": route["id"],
        "distance_m": route["distance_m"],
        "duration_s": route["duration_s"],
        "polyline": route.get("polyline", ""),
        "safety_score": scoring.safety_score(hazard_cost),
        "hazard_summary": summary,
        "hazards": hazards,
        **scoring.route_coverage(assessed_count, len(segments)),
    }


def _serialize_route(route):
    return {
        "id": route["id"],
        "distanceM": route["distance_m"],
        "durationS": route["duration_s"],
        "safetyScore": round(route["safety_score"], 1),
        "rank": round(route["rank"], 2),
        "recommended": route["recommended"],
        "polyline": route["polyline"],
        "assessedSegments": route["assessed_segments"],
        "totalSegments": route["total_segments"],
        "imageryCoverage": round(route["imagery_coverage"], 3),
        "assessed": route["assessed"],
        "hazards": route["hazards"],
    }


@api_bp.get("/health")
def health():
    return jsonify({"status": "ok"})


@api_bp.post("/route")
def create_route():
    cleaned, err = schemas.validate_route_request(request.get_json(silent=True))
    if err:
        return _error(err, 400)

    try:
        origin = routing.geocode(cleaned["origin"])
        destination = routing.geocode(cleaned["destination"])
        routes = routing.get_routes(origin, destination)
    except LocationError as exc:
        return _error(str(exc), 400)
    except UpstreamError as exc:
        return _error(str(exc), 502)

    preference = llm.parse_preference(cleaned["preference"])
    class_weights = scoring.resolve_class_weights(preference["avoid_classes"])

    db_path = _db_path()
    assessed = [_assess_route(route, class_weights, db_path) for route in routes]
    min_duration = min(a["duration_s"] for a in assessed)
    for route in assessed:
        route["rank"] = scoring.rank_route(
            route["safety_score"], route["duration_s"], min_duration, preference["alpha"]
        )
    # Assessed routes never rank below unassessed ones (FR-019).
    assessed.sort(key=lambda a: (a["assessed"], a["rank"]), reverse=True)
    for i, route in enumerate(assessed):
        route["recommended"] = i == 0

    recommended = assessed[0]
    explanation = llm.explain(recommended, assessed[1:])

    db.purge_expired_query_logs(db_path, _config("LOG_RETENTION_DAYS", Config.LOG_RETENTION_DAYS))
    serialized = [_serialize_route(r) for r in assessed]
    response = {
        "queryId": db.log_query(
            db_path,
            cleaned["origin"],
            cleaned["destination"],
            cleaned["preference"],
            recommended["id"],
            {"routes": serialized},
        ),
        "recommendedRouteId": recommended["id"],
        "preference": {
            "alpha": preference["alpha"],
            "avoidClasses": preference["avoid_classes"],
            "interpreted": preference["interpreted"],
        },
        "explanation": explanation,
        "routes": serialized,
    }
    return jsonify(response)


@api_bp.get("/hazards")
def list_hazards():
    query_id = request.args.get("queryId", type=int)
    if query_id is None:
        return _error("queryId is required", 400)
    row = db.get_query(_db_path(), query_id)
    if not row:
        return _error("query not found", 404)
    summary = json.loads(row.get("result_summary") or "{}")
    hazards = []
    for route in summary.get("routes", []):
        hazards.extend(route.get("hazards", []))
    return jsonify(hazards)
