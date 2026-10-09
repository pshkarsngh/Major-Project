import math

from backend.services import segmentation


def test_segments_a_straight_line_into_roughly_equal_parts():
    # ~0.003 deg latitude ~= 333.6 m
    points = [(12.000, 74.000), (12.003, 74.000)]
    segs = segmentation.segment_route(points, target_length_m=100.0)
    assert len(segs) >= 3
    for seg in segs[:-1]:
        assert math.isclose(seg["length_m"], 100.0, abs_tol=1.0)


def test_segment_lengths_sum_to_route_length():
    points = [(12.000, 74.000), (12.003, 74.000)]
    segs = segmentation.segment_route(points, target_length_m=100.0)
    total = sum(s["length_m"] for s in segs)
    assert math.isclose(total, segmentation._haversine(*points), rel_tol=1e-6)


def test_midpoint_lies_between_segment_endpoints():
    points = [(12.000, 74.000), (12.003, 74.000)]
    for seg in segmentation.segment_route(points, target_length_m=100.0):
        assert min(seg["start_lat"], seg["end_lat"]) <= seg["midpoint_lat"] <= max(
            seg["start_lat"], seg["end_lat"]
        )


def test_too_few_points_returns_empty():
    assert segmentation.segment_route([], 100) == []
    assert segmentation.segment_route([(12.0, 74.0)], 100) == []
