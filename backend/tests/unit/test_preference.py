from backend.services import llm


def test_empty_preference_uses_balanced_default():
    result = llm.parse_preference("")
    assert result == {"alpha": 0.5, "avoid_classes": [], "interpreted": False}


def test_missing_api_key_falls_back(monkeypatch):
    monkeypatch.setattr(llm.Config, "LLM_API_KEY", "")
    result = llm.parse_preference("take the safest route only")
    assert result["interpreted"] is False
    assert result["alpha"] == 0.5


def test_valid_json_is_parsed(monkeypatch):
    monkeypatch.setattr(
        llm,
        "_chat",
        lambda *a, **k: '{"alpha": 0.9, "avoidClasses": ["pothole", "bogus"]}',
    )
    result = llm.parse_preference("avoid potholes")
    assert result["interpreted"] is True
    assert result["alpha"] == 0.9
    assert result["avoid_classes"] == ["pothole"]  # invalid class filtered out


def test_invalid_json_falls_back(monkeypatch):
    monkeypatch.setattr(llm, "_chat", lambda *a, **k: "not json")
    result = llm.parse_preference("avoid potholes")
    assert result["interpreted"] is False


def test_alpha_is_clamped(monkeypatch):
    monkeypatch.setattr(llm, "_chat", lambda *a, **k: '{"alpha": 5, "avoidClasses": []}')
    assert llm.parse_preference("safest")["alpha"] == 1.0
