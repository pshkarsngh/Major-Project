from backend.services import scoring


def test_segment_hazard_cost_sums_weighted_confidence():
    detections = [
        {"hazard_class": "pothole", "confidence": 0.9, "severity": "high", "severity_weight": 3},
        {"hazard_class": "crack", "confidence": 0.5, "severity": "low", "severity_weight": 1},
    ]
    # 3.0*3*0.9 + 1.5*1*0.5 = 8.1 + 0.75
    assert scoring.segment_hazard_cost(detections) == 8.85


def test_route_hazard_cost_is_mean():
    assert scoring.route_hazard_cost([2.0, 4.0]) == 3.0
    assert scoring.route_hazard_cost([]) == 0.0


def test_safety_score_is_100_with_no_hazards_and_bounded():
    assert scoring.safety_score(0.0) == 100.0
    assert 0.0 < scoring.safety_score(100.0) < 100.0


def test_safety_score_decreases_with_more_hazards():
    assert scoring.safety_score(1.0) > scoring.safety_score(10.0)


def test_rank_alpha_extremes():
    assert scoring.rank_route(90.0, 1000, 800, alpha=1.0) == 90.0
    # alpha=0 -> time term normalized to best duration
    assert scoring.rank_route(0.0, 1000, 800, alpha=0.0) == 80.0


def test_resolve_class_weights_boosts_avoided_classes():
    weights = scoring.resolve_class_weights(["pothole"])
    assert weights["pothole"] == scoring.Config.CLASS_WEIGHTS["pothole"] * 2
    assert weights["crack"] == scoring.Config.CLASS_WEIGHTS["crack"]


def test_route_coverage_counts_assessed_segments():
    cov = scoring.route_coverage(3, 4)
    assert cov == {
        "assessed_segments": 3,
        "total_segments": 4,
        "imagery_coverage": 0.75,
        "assessed": True,
    }


def test_route_coverage_zero_assessed_is_unassessed():
    cov = scoring.route_coverage(0, 4)
    assert cov["assessed"] is False
    assert cov["imagery_coverage"] == 0.0


def test_route_coverage_handles_no_segments():
    cov = scoring.route_coverage(0, 0)
    assert cov["assessed"] is False
    assert cov["total_segments"] == 0
