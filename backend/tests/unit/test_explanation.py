from backend.services import llm


def _route(route_id, duration_s, safety):
    return {
        "id": route_id,
        "duration_s": duration_s,
        "safety_score": safety,
        "hazard_summary": {"pothole": 4},
    }


def test_explanation_generated_on_success(monkeypatch):
    monkeypatch.setattr(llm, "_chat", lambda *a, **k: "Safer route with fewer potholes.")
    result = llm.explain(_route("r1", 1080, 91.0), [_route("r2", 900, 68.0)])
    assert result["generated"] is True
    assert "potholes" in result["text"]


def test_explanation_degrades_on_failure(monkeypatch):
    monkeypatch.setattr(llm, "_chat", lambda *a, **k: None)
    result = llm.explain(_route("r1", 1080, 91.0), [_route("r2", 900, 68.0)])
    assert result == {"text": "", "generated": False}
