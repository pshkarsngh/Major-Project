# TRD: SafeRoute AI - Safety-Aware Navigation

**Status**: Draft
**Date**: 2026-10-09
**Related docs**: `PRD.md`, `specs/001-safe-route-navigation/plan.md`, `research.md`, `data-model.md`, `contracts/openapi.yaml`

## 1. Purpose

Technical design for SafeRoute AI: how the safety-aware routing pipeline is built,
what components exist, the data model, interfaces, algorithms, and non-functional
requirements. Implementation details and task breakdown live in `tasks.md`.

## 2. Architecture

Six layers (from the feature spec), implemented as a Flask web application:

```
UI (HTML/CSS/JS + Google Maps JS SDK)
  -> Routing Layer (Flask API: geocode, directions, polyline decode, segmentation)
  -> CV Hazard Detection Layer (YOLOv8 + crack severity)
  -> Safety Scoring Engine (hazard cost -> Safety Score -> rank)
  -> LLM Layer (preference parsing + explanation)
  -> Data Storage Layer (SQLite: image metadata, detection cache, query logs)
```

Request flow: UI -> routing -> segmentation -> imagery lookup -> vision -> scoring
-> ranking -> LLM explanation -> response (route, score, hazards, explanation).

## 3. Technology Stack

| Concern | Choice |
|---------|--------|
| Language | Python 3.11 |
| Backend | Flask |
| CV model | YOLOv8 (Ultralytics), fine-tuned from COCO weights |
| Image preprocessing | OpenCV (resize 640x640, CLAHE, color-space conversion) |
| Routing/geocoding | Google Maps Directions API (`alternatives=true`) + Geocoding API |
| LLM | Hosted chat/completion API, strict JSON output, env-configured provider |
| Storage | SQLite (single file); imagery on local disk |
| Frontend | HTML/CSS/JS, Google Maps JavaScript SDK |
| Testing | pytest (unit, contract, integration) |

## 4. Components

```
backend/
├── app.py              Flask app factory, static serving, error handling
├── config.py           Env-driven config + constants
├── api/routes.py       /api/route, /api/hazards, /api/health
├── services/
│   ├── routing.py      geocode + directions + polyline decode
│   ├── segmentation.py split route into equal-length segments
│   ├── imagery.py      segment midpoint -> nearest road image
│   ├── vision.py       YOLOv8 detection + severity + class weights
│   ├── scoring.py      hazard cost, Safety Score, ranking
│   └── llm.py          preference parsing + explanation
├── storage/{db.py, schema.sql}
├── data/images/        local road imagery
└── tests/{unit,contract,integration}/
frontend/{index.html, css/style.css, js/app.js}
ml/{weights/best.pt, training/}
```

## 5. Algorithms

**Detection**: for image I, detections `H(I) = {(c_m, p_m, b_m)}`; drop any with
`p_m < tau` (tau = 0.4). Crack severity low/medium/high from box size and aspect ratio.

**Per-segment hazard cost**:
```
H_j = sum over detections m in segment j of ( gamma_cm * w_m * p_m )
```
where `gamma_c` is the class weight and `w_m` in {1,2,3} is severity.

**Route hazard cost and Safety Score** (lambda = 0.15):
```
H_i = (1 / N_i) * sum_j H_j
SafetyScore(r_i) = 100 * e^(-lambda * H_i)      # in (0, 100]
```

**Ranking** (alpha in [0,1] is the safety/time weight):
```
Rank(r_i) = alpha * SafetyScore(r_i) + (1 - alpha) * 100 * (t_min / t_i)
```
`avoidClasses` increase their `gamma_c`. Default `alpha = 0.5`, `avoidClasses = []`
when no valid preference.

**Segmentation**: `N_i = ceil(d_i / L)`, L in 200-500 m (default 300 m); midpoints
used for imagery lookup.

**Preference parsing**: LLM returns strict JSON `{alpha, avoidClasses}`; invalid output
-> balanced fallback with `interpreted=false`.

## 6. Data Model

SQLite tables (full detail in `data-model.md`):

- **road_image**: id PK, file_path, lat, lng, captured_at.
- **hazard_detection** (cache): id PK, image_id FK, segment_index, hazard_class,
  confidence, bbox, severity, class_weight.
- **query_log**: id PK, origin_text, dest_text, preference_text, created_at,
  recommended_route_id, result_summary (JSON).

Enums: `hazard_class` = pothole | crack | damaged_patch | waterlogging |
uneven_surface; `severity` = low | medium | high. Routes/Segments are computed
per request; only detections and logs are persisted.

## 7. API Contracts

Full schema: `contracts/openapi.yaml`.

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health` | liveness |
| POST | `/api/route` | body `{origin, destination, preference?}` -> ranked routes, recommendation, explanation |
| GET | `/api/hazards?queryId=` | cached detections for a logged query |

Response invariants: `safetyScore` in [0,100]; exactly one route with
`recommended=true`; `preference.interpreted` false on fallback; `explanation.generated`
false on LLM failure.

## 8. Configuration

Env vars (from `backend/config.py`):

```
GOOGLE_MAPS_API_KEY
LLM_API_KEY
LLM_MODEL
SAFETY_DECAY_LAMBDA=0.15
DETECTION_CONFIDENCE_THRESHOLD=0.4
SEGMENT_LENGTH_M=300
SQLITE_PATH
```

## 9. Non-Functional Requirements

- **Performance**: end-to-end recommendation for <=20 km, <=3 alternatives within
  ~45 s p95 (dominated by per-segment inference + LLM). Detection results cached.
- **Reliability**: external calls have timeouts and defined fallbacks; missing imagery
  -> neutral segment; LLM failure -> routes returned without explanation.
- **Security**: all API keys server-side only; validate and bound all request fields;
  no secrets in frontend or repo.
- **Scalability**: prototype scale (single city, tens of concurrent requests).
- **Observability**: request latency logging on the recommendation path.

## 10. Testing Strategy

- **Unit**: scoring math, segmentation, preference fallback (pure functions).
- **Contract**: `/api/route` and `/api/hazards` shapes vs `openapi.yaml`.
- **Integration**: mocked routing + LLM, end-to-end request path; vision on a small
  fixed image set.
- External services are mocked (non-deterministic, cost money) at the service boundary.

## 11. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| LLM hallucination / unparseable output | Strict JSON schema + fallback + degrade |
| Stale imagery | Capture-time metadata; future crowdsourcing/live feeds |
| Detector generalization | Report precision/recall/mAP; expand training data |
| API quota/cost | Cache detections; cap alternatives; server-side batching |
| CPU inference latency | Caching, cap segments, batch inference |

## 12. Deployment

Single Flask process serving the API and static frontend. SQLite file + imagery
directory on the host. Runs on Linux (dev on Windows). API keys via environment.
No containerization or orchestration required at prototype scale.
