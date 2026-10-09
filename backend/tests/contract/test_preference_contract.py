def test_preference_object_reflects_parse(client, mock_services, monkeypatch):
    monkeypatch.setattr(
        mock_services.llm,
        "parse_preference",
        lambda text, **kwargs: {"alpha": 0.8, "avoid_classes": ["pothole"], "interpreted": True},
    )
    data = client.post(
        "/api/route", json={"origin": "A", "destination": "B", "preference": "avoid potholes"}
    ).get_json()
    preference = data["preference"]
    assert preference["interpreted"] is True
    assert preference["alpha"] == 0.8
    assert preference["avoidClasses"] == ["pothole"]


def test_fallback_preference_when_uninterpreted(client, mock_services, monkeypatch):
    monkeypatch.setattr(
        mock_services.llm,
        "parse_preference",
        lambda text, **kwargs: {"alpha": 0.5, "avoid_classes": [], "interpreted": False},
    )
    data = client.post(
        "/api/route", json={"origin": "A", "destination": "B", "preference": "???"}
    ).get_json()
    assert data["preference"]["interpreted"] is False
    assert data["preference"]["alpha"] == 0.5
