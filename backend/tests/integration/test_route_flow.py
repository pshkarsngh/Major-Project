def test_full_flow_returns_ranked_routes_with_one_recommendation(client, mock_services):
    response = client.post("/api/route", json={"origin": "Moodbidri", "destination": "Mangalore"})
    assert response.status_code == 200
    data = response.get_json()
    assert len(data["routes"]) == 2
    assert sum(1 for r in data["routes"] if r["recommended"]) == 1


def test_missing_imagery_marks_route_unassessed(client, mock_services):
    """No images in the DB -> no assessed segments -> route flagged unassessed, request succeeds."""
    data = client.post("/api/route", json={"origin": "A", "destination": "B"}).get_json()
    for route in data["routes"]:
        assert route["assessed"] is False
        assert route["assessedSegments"] == 0
        assert route["imageryCoverage"] == 0.0


def test_fastest_preference_recommends_shortest_trip(client, mock_services, monkeypatch):
    monkeypatch.setattr(
        mock_services.llm,
        "parse_preference",
        lambda text, **kwargs: {"alpha": 0.0, "avoid_classes": [], "interpreted": True},
    )
    data = client.post(
        "/api/route", json={"origin": "A", "destination": "B", "preference": "fastest"}
    ).get_json()
    assert data["recommendedRouteId"] == "r1"  # r1 is 900s vs r2 1080s


def test_hazard_heavy_route_ranks_below_clean_route(client, mock_services, monkeypatch):
    routes = [
        {
            "id": "r1",
            "distance_m": 8000,
            "duration_s": 900,
            "polyline": "",
            "points": [(12.00, 74.00), (12.02, 74.02)],
        },
        {
            "id": "r2",
            "distance_m": 8000,
            "duration_s": 900,
            "polyline": "",
            "points": [(13.00, 75.00), (13.02, 75.02)],
        },
    ]
    monkeypatch.setattr(mock_services.routing, "get_routes", lambda o, d, **k: routes)
    monkeypatch.setattr(
        mock_services.imagery,
        "find_nearest_image",
        lambda lat, lng, **kwargs: (
            {"id": 1, "file_path": "hazard.jpg"}
            if lng < 74.5
            else {"id": 2, "file_path": "clean.jpg"}
        ),
    )
    monkeypatch.setattr(
        mock_services.vision,
        "detect",
        lambda image_path, **kwargs: (
            [
                {
                    "hazard_class": "pothole",
                    "confidence": 0.9,
                    "severity": "high",
                    "severity_weight": 3,
                    "class_weight": 3.0,
                }
            ]
            if "hazard.jpg" in image_path
            else []
        ),
    )
    monkeypatch.setattr(mock_services.db, "get_cached_detections", lambda db_path, image_id: [])
    monkeypatch.setattr(mock_services.db, "save_detections", lambda *a, **k: {})
    monkeypatch.setattr(
        mock_services.llm,
        "parse_preference",
        lambda text, **kwargs: {"alpha": 0.5, "avoid_classes": [], "interpreted": True},
    )

    data = client.post("/api/route", json={"origin": "A", "destination": "B"}).get_json()
    by_id = {r["id"]: r for r in data["routes"]}
    assert by_id["r1"]["safetyScore"] < by_id["r2"]["safetyScore"]
    assert by_id["r1"]["assessed"] and by_id["r2"]["assessed"]
    assert data["recommendedRouteId"] == "r2"


def test_unassessed_route_never_recommended_over_assessed(client, mock_services, monkeypatch):
    routes = [
        {
            "id": "r1",
            "distance_m": 8000,
            "duration_s": 900,
            "polyline": "",
            "points": [(12.00, 74.00), (12.02, 74.02)],
        },
        {
            "id": "r2",
            "distance_m": 8000,
            "duration_s": 1200,
            "polyline": "",
            "points": [(13.00, 75.00), (13.02, 75.02)],
        },
    ]
    monkeypatch.setattr(mock_services.routing, "get_routes", lambda o, d, **k: routes)
    # Only route r1 has imagery; r2 is fully unassessed and (despite being scored 100) must not win.
    monkeypatch.setattr(
        mock_services.imagery,
        "find_nearest_image",
        lambda lat, lng, **kwargs: ({"id": 1, "file_path": "img.jpg"} if lng < 74.5 else None),
    )
    monkeypatch.setattr(
        mock_services.vision,
        "detect",
        lambda image_path, **kwargs: [
            {
                "hazard_class": "pothole",
                "confidence": 0.9,
                "severity": "high",
                "severity_weight": 3,
                "class_weight": 3.0,
            }
        ],
    )
    monkeypatch.setattr(mock_services.db, "get_cached_detections", lambda db_path, image_id: [])
    monkeypatch.setattr(mock_services.db, "save_detections", lambda *a, **k: {})

    data = client.post("/api/route", json={"origin": "A", "destination": "B"}).get_json()
    by_id = {r["id"]: r for r in data["routes"]}
    assert by_id["r1"]["assessed"] is True
    assert by_id["r2"]["assessed"] is False
    assert data["recommendedRouteId"] == "r1"
