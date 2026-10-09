from backend.services.errors import UpstreamError, LocationError


def test_route_response_shape(client, mock_services):
    response = client.post("/api/route", json={"origin": "A", "destination": "B"})
    assert response.status_code == 200
    data = response.get_json()

    assert {"queryId", "recommendedRouteId", "preference", "explanation", "routes"} <= set(data)
    assert data["recommendedRouteId"] in [r["id"] for r in data["routes"]]

    recommended = [r for r in data["routes"] if r["recommended"]]
    assert len(recommended) == 1

    for route in data["routes"]:
        assert {"id", "distanceM", "durationS", "safetyScore", "rank", "recommended", "polyline", "hazards"} <= set(route)
        assert 0.0 <= route["safetyScore"] <= 100.0
        assert isinstance(route["hazards"], list)


def test_preference_and_explanation_shape(client, mock_services):
    data = client.post("/api/route", json={"origin": "A", "destination": "B"}).get_json()
    assert {"alpha", "avoidClasses", "interpreted"} <= set(data["preference"])
    assert 0.0 <= data["preference"]["alpha"] <= 1.0
    assert {"text", "generated"} <= set(data["explanation"])


def test_route_coverage_fields_shape(client, mock_services):
    data = client.post("/api/route", json={"origin": "A", "destination": "B"}).get_json()
    for route in data["routes"]:
        assert {"assessedSegments", "totalSegments", "imageryCoverage", "assessed"} <= set(route)
        assert route["assessedSegments"] <= route["totalSegments"]
        assert 0.0 <= route["imageryCoverage"] <= 1.0
        assert isinstance(route["assessed"], bool)


def test_missing_origin_returns_400(client):
    response = client.post("/api/route", json={"destination": "B"})
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_unresolvable_location_returns_400(client, mock_services, monkeypatch):
    def boom(address, **kwargs):
        raise LocationError("not found")

    monkeypatch.setattr(mock_services.routing, "geocode", boom)
    response = client.post("/api/route", json={"origin": "X", "destination": "B"})
    assert response.status_code == 400


def test_routing_outage_returns_502(client, mock_services, monkeypatch):
    def boom(origin, destination, **kwargs):
        raise UpstreamError("routing down")

    monkeypatch.setattr(mock_services.routing, "get_routes", boom)
    response = client.post("/api/route", json={"origin": "A", "destination": "B"})
    assert response.status_code == 502
