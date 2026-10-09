"""Safety Score and route ranking (spec FR-008, FR-009, FR-012).

Formulas (research R5/R6):
    H_j  = sum(gamma_c * w * p)                per segment
    H_i  = mean(H_j)                           per route
    SafetyScore = 100 * e^(-lambda * H_i)      lambda = 0.15
    Rank = alpha * SafetyScore + (1-alpha) * 100 * (t_min / t_i)
"""
import math

from ..config import Config


def severity_weight(severity):
    return Config.SEVERITY_WEIGHTS.get(severity, 1)


def segment_hazard_cost(detections, class_weights=None):
    """H_j for one segment. `detections` are vision.detect() dicts."""
    class_weights = class_weights or Config.CLASS_WEIGHTS
    total = 0.0
    for d in detections:
        gamma = class_weights.get(d["hazard_class"], Config.CLASS_WEIGHTS.get(d["hazard_class"], 1.0))
        w = d.get("severity_weight", severity_weight(d.get("severity", "low")))
        total += gamma * w * float(d["confidence"])
    return total


def route_hazard_cost(segment_costs):
    """H_i, the mean per-segment hazard cost over ASSESSED segments only (FR-019).

    Callers pass costs for assessed segments; unassessed segments are excluded.
    """
    if not segment_costs:
        return 0.0
    return sum(segment_costs) / len(segment_costs)


def route_coverage(assessed_count, total_count):
    """Imagery coverage for a route (FR-019). Assessed means >=1 usable segment."""
    if total_count <= 0:
        return {
            "assessed_segments": 0,
            "total_segments": 0,
            "imagery_coverage": 0.0,
            "assessed": False,
        }
    return {
        "assessed_segments": assessed_count,
        "total_segments": total_count,
        "imagery_coverage": assessed_count / total_count,
        "assessed": assessed_count > 0,
    }


def safety_score(hazard_cost, decay=None):
    """0-100; higher means safer."""
    decay = Config.SAFETY_DECAY_LAMBDA if decay is None else decay
    score = 100.0 * math.exp(-decay * hazard_cost)
    return max(0.0, min(100.0, score))


def rank_route(safety, duration_s, min_duration_s, alpha=0.5):
    """Combine safety and time. Time term is normalized to the fastest candidate."""
    alpha = max(0.0, min(1.0, alpha))
    time_term = 100.0 if duration_s <= 0 else 100.0 * (min_duration_s / duration_s)
    return alpha * safety + (1 - alpha) * time_term


def resolve_class_weights(avoid_classes):
    """Boost gamma_c for hazard classes the user asked to avoid."""
    weights = dict(Config.CLASS_WEIGHTS)
    for cls in avoid_classes or []:
        if cls in weights:
            weights[cls] = weights[cls] * 2.0
    return weights
