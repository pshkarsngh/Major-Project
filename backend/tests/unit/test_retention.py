from datetime import datetime, timedelta, timezone

from backend.storage import db


def _seed_query(db_path, days_ago):
    created = datetime.now(timezone.utc) - timedelta(days=days_ago)
    conn = db.connect(db_path)
    try:
        conn.execute(
            "INSERT INTO query_log (origin_text, dest_text, created_at) VALUES (?,?,?)",
            ("A", "B", created.isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def test_purge_removes_only_expired_logs(tmp_path):
    db_path = str(tmp_path / "retention.db")
    db.init_db(db_path)
    _seed_query(db_path, days_ago=1)
    _seed_query(db_path, days_ago=40)

    removed = db.purge_expired_query_logs(db_path, retention_days=30)

    assert removed == 1
    rows = db.connect(db_path).execute("SELECT COUNT(*) AS c FROM query_log").fetchone()
    assert rows["c"] == 1


def test_purge_keeps_all_when_none_expired(tmp_path):
    db_path = str(tmp_path / "retention2.db")
    db.init_db(db_path)
    _seed_query(db_path, days_ago=5)

    assert db.purge_expired_query_logs(db_path, retention_days=30) == 0
