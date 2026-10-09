CREATE TABLE IF NOT EXISTS road_image (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path   TEXT NOT NULL,
    lat         REAL NOT NULL,
    lng         REAL NOT NULL,
    captured_at TEXT
);

CREATE TABLE IF NOT EXISTS hazard_detection (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    image_id      INTEGER,
    segment_index INTEGER,
    hazard_class  TEXT NOT NULL
        CHECK (hazard_class IN ('pothole','crack','damaged_patch','waterlogging','uneven_surface')),
    confidence    REAL NOT NULL,
    bbox          TEXT,
    severity      TEXT NOT NULL DEFAULT 'low'
        CHECK (severity IN ('low','medium','high')),
    class_weight  REAL NOT NULL DEFAULT 1.0,
    FOREIGN KEY (image_id) REFERENCES road_image(id)
);

CREATE TABLE IF NOT EXISTS query_log (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    origin_text         TEXT NOT NULL,
    dest_text           TEXT NOT NULL,
    preference_text     TEXT,
    created_at          TEXT NOT NULL,
    recommended_route_id TEXT,
    result_summary      TEXT
);
