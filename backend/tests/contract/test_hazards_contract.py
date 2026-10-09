def _patch_hazards(monkeypatch, routes):
    monkeypatch.setattr(
        routes.imagery,
        "find_nearest_image",
        lambda lat, lng, **kwargs: {"id": 1, "file_path": "hazard.jpg"},
    )
    monkeypatch.setattr(
        routes.vision,
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
    monkeypatch.setattr(routes.db, "get_cached_detections", lambda db_path, image_id: [])
    monkeypatch.setattr(routes.db, "save_detections", lambda *a, **k: None)


def test_hazards_endpoint_returns_detected_hazards(client, mock_services, monkeypatch):
    _patch_hazards(monkeypatch, mock_services)
    query_id = client.post("/api/route", json={"origin": "A", "destination": "B"}).get_json()["queryId"]

    response = client.get(f"/api/hazards?queryId={query_id}")
    assert response.status_code == 200
    hazards = response.get_json()
    assert isinstance(hazards, list) and hazards
    for hazard in hazards:
        assert {"class", "confidence", "severity", "lat", "lng"} <= set(hazard)


def test_hazards_requires_query_id(client):
    assert client.get("/api/hazards").status_code == 400


def test_hazards_unknown_query_returns_404(client):
    assert client.get("/api/hazards?queryId=9999").status_code == 404
