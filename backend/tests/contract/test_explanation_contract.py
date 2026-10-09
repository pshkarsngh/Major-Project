def test_explanation_present_when_generated(client, mock_services, monkeypatch):
    monkeypatch.setattr(
        mock_services.llm,
        "explain",
        lambda recommended, alternatives, **kwargs: {
            "text": "Slightly longer but far fewer potholes (91 vs 68).",
            "generated": True,
        },
    )
    explanation = client.post("/api/route", json={"origin": "A", "destination": "B"}).get_json()["explanation"]
    assert explanation["generated"] is True
    assert explanation["text"]


def test_routes_still_returned_when_explanation_fails(client, mock_services, monkeypatch):
    monkeypatch.setattr(
        mock_services.llm,
        "explain",
        lambda recommended, alternatives, **kwargs: {"text": "", "generated": False},
    )
    data = client.post("/api/route", json={"origin": "A", "destination": "B"}).get_json()
    assert data["explanation"]["generated"] is False
    assert len(data["routes"]) == 2
