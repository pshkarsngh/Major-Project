from datetime import datetime, timedelta, timezone

from backend.services import imagery

NOW = datetime(2026, 10, 9, tzinfo=timezone.utc)


def _image(captured_at):
    return {"id": 1, "file_path": "x.jpg", "lat": 12.0, "lng": 74.0, "captured_at": captured_at}


def test_fresh_image_is_not_stale():
    fresh = (NOW - timedelta(days=10)).isoformat()
    assert imagery.is_stale(_image(fresh), reference=NOW, staleness_days=180) is False


def test_old_image_is_stale():
    old = (NOW - timedelta(days=200)).isoformat()
    assert imagery.is_stale(_image(old), reference=NOW, staleness_days=180) is True


def test_image_without_capture_time_is_stale():
    assert imagery.is_stale(_image(None), reference=NOW, staleness_days=180) is True


def test_image_with_invalid_capture_time_is_stale():
    assert imagery.is_stale(_image("not-a-date"), reference=NOW, staleness_days=180) is True
