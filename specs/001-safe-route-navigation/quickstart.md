# Quickstart: SafeRoute AI

Validation guide to prove the feature works end-to-end. See
[data-model.md](./data-model.md) for entity details and
[contracts/openapi.yaml](./contracts/openapi.yaml) for exact API shapes.
Implementation details belong in `tasks.md`, not here.

## Prerequisites

- Python 3.11 and `pip`
- A Google Maps API key with Directions + Geocoding enabled
- An LLM API key (chat/completion endpoint with JSON output)
- Trained YOLOv8 weights at `ml/weights/best.pt` (or download a pre-trained placeholder)
- Local road imagery under `backend/data/images/` with location + capture-time metadata

## Configuration

Set environment variables (names are indicative; defined in `backend/config.py`):

```text
GOOGLE_MAPS_API_KEY=...
LLM_API_KEY=...
LLM_MODEL=...
SAFETY_DECAY_LAMBDA=0.15
DETECTION_CONFIDENCE_THRESHOLD=0.4
SEGMENT_LENGTH_M=300
IMAGERY_STALENESS_DAYS=180
LOG_RETENTION_DAYS=30
```

## Setup

```text
python -m venv .venv
.venv\Scripts\activate            # Windows PowerShell
pip install -r backend/requirements.txt
```

## Run

```text
python backend/app.py
```

Backend serves the API and the static frontend (default http://localhost:5000).

## Validation Scenarios

### 1. Health check

```text
curl http://localhost:5000/api/health
```

Expected: `{"status":"ok"}`.

### 2. Core recommendation (User Story 1, P1)

```text
curl -X POST http://localhost:5000/api/route -H "Content-Type: application/json" ^
  -d "{\"origin\":\"Moodbidri\",\"destination\":\"Mangalore Central\"}"
```

Expected:
- HTTP 200 with `routes` containing 2-4 alternatives.
- Every route has a `safetyScore` in [0, 100] and a `durationS`.
- Exactly one route has `recommended: true`.
- Every route reports `assessedSegments`, `totalSegments`, `imageryCoverage` (0-1), and `assessed`.

### 3. Safety preference changes ranking (User Story 2, P2)

Send the same request twice with different `preference` values:

```text
"take the safest route only"     -> safety dominates
"fastest route, I'm in a hurry"  -> time dominates
```

Expected: the recommended route changes in the stated direction; `preference.interpreted`
is `true`. With an empty/garbled preference, `interpreted` is `false` and a result is
still returned.

### 4. Explanation present (User Story 3, P3)

From the response in scenario 2, check `explanation`.

Expected: `explanation.generated: true` and text referencing the recommended route's
time and safety vs at least one alternative.

### 5. Coverage and degradation (FR-019, SC-008, SC-009)

- Remove some segments' images from `backend/data/images/`.
  Expected: request still succeeds; unassessed segments are excluded from the
  average; `imageryCoverage` drops below 1 and `assessedSegments < totalSegments`.
- Remove all imagery for one candidate route.
  Expected: that route has `assessed: false` and is not recommended over an assessed
  route.
- Point the LLM key at an invalid value.
  Expected: routes are still returned; `explanation.generated: false`.

### 6. Stale imagery (FR-018, SC-011)

Set an image's `captured_at` older than `IMAGERY_STALENESS_DAYS` (default 180).

Expected: the image is not used for scoring; that segment counts as unassessed and
coverage reflects the exclusion.

### 7. Log retention and privacy (FR-020, SC-010)

Insert a query-log row with `created_at` older than `LOG_RETENTION_DAYS` (default 30),
trigger a purge (on startup/next query), then read logs.

Expected: the old row is deleted; origin/destination/preference text is not exposed
outside the routing/LLM calls.

### 8. Latency (SC-001)

Time a request for a <=20 km trip with up to 3 alternatives.

Expected: p95 end-to-end latency under 45 seconds (with detection caching enabled).

## Automated Tests

```text
pytest backend/tests/unit          # scoring, segmentation, preference fallback
pytest backend/tests/integration   # mocked routing + LLM, end-to-end request
pytest backend/tests/contract      # API shape matches contracts/openapi.yaml
```

External services are mocked in tests; vision inference runs against a small fixed
image set. All suites should pass before considering the feature complete.
