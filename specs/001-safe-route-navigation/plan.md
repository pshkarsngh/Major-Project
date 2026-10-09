# Implementation Plan: SafeRoute AI - Safety-Aware Navigation

**Branch**: `001-safe-route-navigation` | **Date**: 2026-10-09 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-safe-route-navigation/spec.md`

## Summary

Build a web application that recommends the safest driving route between two points.
It fetches multiple candidate routes from a routing service, splits each into
~200-500 m segments, runs a multi-class road-hazard detector over segment imagery,
converts detections into a 0-100 Safety Score, ranks routes by combining that score
with travel time according to an optional natural-language preference, and returns a
plain-language explanation of the recommendation.

Per the clarification session (spec `## Clarifications`), the Safety Score is computed
only over assessed segments (those with usable imagery), routes report imagery
coverage, stale imagery (older than a configurable cutoff, default 180 days) is
excluded from scoring, and query logs are retained for 30 days as personal data.

Technical approach: a Python/Flask backend exposing REST endpoints for a React
(Vite) frontend; YOLOv8 (via Ultralytics) for hazard detection; OpenCV for
preprocessing; Google Maps Directions/Geocoding APIs for routing and geocoding; a
hosted LLM chat/completion API with strict JSON output for preference parsing and
explanation; SQLite for caching detections and logging queries.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: Flask, Ultralytics (YOLOv8), OpenCV, `requests`/Google Maps
Directions + Geocoding APIs, a hosted LLM chat/completion API, SQLite (stdlib);
React + Vite for the frontend

**Storage**: SQLite (single-file, local) for detections cache, query logs, and image
metadata; road imagery stored on disk

**Testing**: pytest (unit + integration) plus contract tests for the REST API

**Target Platform**: Web application — Flask backend on Linux, browser-based
frontend (Google Maps JavaScript SDK)

**Project Type**: Web application (backend + frontend)

**Performance Goals**: End-to-end recommendation for a <=20 km trip with up to 3
alternatives returned in under ~45 s (p95), dominated by per-segment inference and
LLM latency

**Constraints**: External API quotas and monetary cost (routing + LLM); LLM output
must be schema-validated to avoid hallucination; road imagery is static and may be
stale (imagery older than the staleness cutoff — default 180 days — is excluded from
scoring); CPU-only inference must remain viable for the prototype; query logs contain
personal data and are deleted after 30 days.

**Scale/Scope**: Prototype scale — a single city, tens of concurrent requests,
routes of up to ~50 segments each, <=3 alternatives per query

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The project constitution at `.specify/memory/constitution.md` is still the unfilled
template — no principles have been ratified. There are therefore no project-specific
gates to enforce at this time.

- **Gate result: PASS (no ratified principles).**
- Action: ratify the constitution before implementation so that testing, simplicity,
  and observability expectations are explicit. Until then, this plan assumes the
  Spec Kit defaults: independent testability, simplest viable design, and clear
  error handling at external boundaries.

Re-check after Phase 1 design: **PASS** — design is modular, boundaries (routing,
vision, scoring, LLM, storage) are isolated behind services, and no unnecessary
projects or abstractions were introduced.

## Project Structure

### Documentation (this feature)

```text
specs/001-safe-route-navigation/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── openapi.yaml
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit.tasks - NOT created here)
```

### Source Code (repository root)

```text
backend/
├── app.py                 # Flask app factory + static frontend serving
├── config.py              # env-driven config (API keys, thresholds, weights)
├── api/
│   ├── __init__.py
│   └── routes.py          # REST endpoints: /api/route, /api/hazards, /api/health
├── services/
│   ├── routing.py         # Google Maps Directions + Geocoding + polyline decode
│   ├── segmentation.py    # split route geometry into equal-length segments
│   ├── imagery.py         # segment midpoint -> road image lookup (dataset)
│   ├── vision.py          # YOLOv8 detection + crack severity classifier
│   ├── scoring.py         # hazard cost, Safety Score, route ranking
│   └── llm.py             # preference parsing + explanation (JSON schema enforced)
├── storage/
│   ├── db.py              # SQLite connection, cache + query log access
│   └── schema.sql         # tables
├── data/
│   └── images/            # local road imagery store (metadata indexed in SQLite)
└── tests/
    ├── contract/
    ├── integration/
    └── unit/

frontend/                  # Vite + React (built to frontend/dist, served by Flask)
├── index.html
├── package.json
├── vite.config.js
└── src/
    ├── main.jsx
    ├── App.jsx
    ├── api.js
    ├── styles.css
    └── components/        # RouteForm, RouteCard, MapView

ml/
├── weights/               # trained YOLOv8 weights (best.pt)
└── training/              # dataset config + training scripts (RDD2020 + extras)
```

**Structure Decision**: Web application layout. `backend/` holds the Flask API and
all services; `frontend/` is a Vite + React single-page app (built to `frontend/dist`
and served by Flask with an SPA fallback, using the Google Maps JavaScript SDK);
`ml/` keeps model training artifacts separate from runtime code. `datasets/` is
intentionally excluded from the repo (large external imagery) and referenced by path
via config.

## Post-Clarification Deltas

The 2026-10-09 clarification session added FR-019, FR-020 and revised FR-018, SC-001,
SC-009..SC-011. Design impact:

- **Coverage-aware scoring**: hazard cost `H_i` is the mean over *assessed* segments
  only; each route reports `assessedSegments`/`totalSegments` (or `imageryCoverage`).
  Routes with zero assessed segments are marked `assessed=false` and never recommended
  over an assessed route.
- **Imagery staleness**: `config.py` gains `IMAGERY_STALENESS_DAYS=180`; imagery beyond
  the cutoff is not used for scoring and reduces reported coverage.
- **Log retention**: query logs are purged after `LOG_RETENTION_DAYS=30`; origin,
  destination, and preference text are treated as personal data.
- **Latency**: SC-001 now fixes the p95 target already stated in Performance Goals.

## Complexity Tracking

> No constitution violations. Section intentionally empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| - | - | - |
