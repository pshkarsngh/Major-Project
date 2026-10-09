"""SQLite persistence: image metadata, detection cache, query logs.

A fresh connection is opened per operation. Connections are not shared across
threads, which keeps Flask's threaded request handling simple at prototype scale.
"""
import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone

_SCHEMA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")


def connect(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path, image_manifest=None):
    """Create tables and seed road_image from a JSON manifest if empty."""
    conn = connect(db_path)
    with open(_SCHEMA, "r", encoding="utf-8") as fh:
        conn.executescript(fh.read())
    if image_manifest and os.path.exists(image_manifest):
        count = conn.execute("SELECT COUNT(*) AS c FROM road_image").fetchone()["c"]
        if count == 0:
            with open(image_manifest, "r", encoding="utf-8") as fh:
                images = json.load(fh)
            for img in images:
                conn.execute(
                    "INSERT INTO road_image (file_path, lat, lng, captured_at) VALUES (?,?,?,?)",
                    (img["file_path"], img["lat"], img["lng"], img.get("captured_at")),
                )
            conn.commit()
    conn.close()


def list_images(db_path):
    conn = connect(db_path)
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM road_image").fetchall()]
    finally:
        conn.close()


def get_cached_detections(db_path, image_id):
    conn = connect(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM hazard_detection WHERE image_id = ?", (image_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def save_detections(db_path, image_id, segment_index, detections):
    conn = connect(db_path)
    try:
        conn.executemany(
            "INSERT INTO hazard_detection (image_id, segment_index, hazard_class, confidence, bbox, severity, class_weight)"
            " VALUES (?,?,?,?,?,?,?)",
            [
                (
                    image_id,
                    segment_index,
                    d["hazard_class"],
                    d["confidence"],
                    json.dumps(d.get("bbox")),
                    d.get("severity", "low"),
                    d.get("class_weight", 1.0),
                )
                for d in detections
            ],
        )
        conn.commit()
    finally:
        conn.close()


def log_query(db_path, origin_text, dest_text, preference_text, recommended_route_id, result_summary):
    conn = connect(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO query_log (origin_text, dest_text, preference_text, created_at, recommended_route_id, result_summary)"
            " VALUES (?,?,?,?,?,?)",
            (
                origin_text,
                dest_text,
                preference_text,
                datetime.now(timezone.utc).isoformat(),
                recommended_route_id,
                json.dumps(result_summary),
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_query(db_path, query_id):
    conn = connect(db_path)
    try:
        row = conn.execute("SELECT * FROM query_log WHERE id = ?", (query_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def purge_expired_query_logs(db_path, retention_days):
    """Delete query logs older than retention_days (FR-020). Returns rows removed."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=retention_days)).isoformat()
    conn = connect(db_path)
    try:
        cur = conn.execute("DELETE FROM query_log WHERE created_at < ?", (cutoff,))
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()
