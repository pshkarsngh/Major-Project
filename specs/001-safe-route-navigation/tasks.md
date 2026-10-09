---
description: "Task list for SafeRoute AI implementation"
---

# Tasks: SafeRoute AI - Safety-Aware Navigation

**Input**: Design documents from `/specs/001-safe-route-navigation/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/openapi.yaml, quickstart.md

**Tests**: Included. The plan and quickstart define a pytest strategy (unit/contract/integration); tests are listed first within each story.

**Organization**: Tasks are grouped by user story so each can be implemented and tested independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1, US2, US3, US4
- Exact file paths are included in every task

## Path Conventions

Web application layout from plan.md: `backend/`, `frontend/`, `ml/`, with tests under `backend/tests/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and structure

- [X] T001 Create the project directory tree per plan: `backend/`, `backend/api/`, `backend/services/`, `backend/storage/`, `backend/data/images/`, `backend/tests/{unit,contract,integration}/`, `frontend/{css,js}/`, `ml/{weights,training}/`, each with `__init__.py` where it is a Python package.
- [X] T002 [P] Create `backend/requirements.txt` pinning: Flask, ultralytics, opencv-python, requests, pyyaml, pytest.
- [X] T003 [P] Create `backend/config.py` reading env vars: `GOOGLE_MAPS_API_KEY`, `LLM_API_KEY`, `LLM_MODEL`, `SAFETY_DECAY_LAMBDA=0.15`, `DETECTION_CONFIDENCE_THRESHOLD=0.4`, `SEGMENT_LENGTH_M=300`, `SQLITE_PATH`. No secrets hard-coded.
- [X] T004 [P] Create `.gitignore` (venv, `__pycache__`, `*.db`, `ml/weights/*.pt`, `backend/data/images/`) and a root `README.md` with setup/run steps.

**Checkpoint**: Structure and config ready.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure required before ANY user story.

**CRITICAL**: No user story work can begin until this phase is complete.

- [X] T005 Create SQLite schema in `backend/storage/schema.sql`: tables `road_image` (id PK, file_path, lat, lng, captured_at), `hazard_detection` (id PK, image_id FK, segment_index, hazard_class, confidence, bbox, severity, class_weight), `query_log` (id PK, origin_text, dest_text, preference_text, created_at, recommended_route_id, result_summary). `hazard_class` restricted to (pothole, crack, damaged_patch, waterlogging, uneven_surface); `severity` to (low, medium, high).
- [X] T006 Implement `backend/storage/db.py`: SQLite connection manager, schema init, detection cache read/write keyed by image id, and query-log append.
- [X] T007 [P] Implement `backend/app.py`: Flask app factory, load config, init DB, serve the `frontend/` static files.
- [X] T008 Implement `backend/api/routes.py` with a `GET /api/health` endpoint returning `{"status":"ok"}` and register the blueprint in `app.py`.
- [X] T009 Add JSON error handling in `backend/app.py`: 400 for bad input, 404, and 502 for upstream failures, all returning the `Error` shape from `contracts/openapi.yaml`.
- [X] T010 [P] Create `ml/training/dataset.yaml` (RDD2020 + waterlogging/uneven classes, 5 classes) and `ml/training/train.py` (Ultralytics YOLOv8 fine-tune from COCO weights, imgsz 640, 70/15/15 split).
- [ ] T011 Fine-tune YOLOv8 using `ml/training/train.py` and export weights to `ml/weights/best.pt`; record class list and metrics. **BLOCKED**: requires the external RDD2020 dataset + `ultralytics` (not runnable in this environment). The training script and `dataset.yaml` are in place (T010); run this once the dataset is prepared.
- [X] T012 Implement `backend/services/imagery.py`: load road-image metadata from `backend/data/images/` and SQLite, and resolve a segment midpoint to the nearest image by geo-proximity (spec FR-004, FR-018).
- [X] T013 Implement `backend/services/vision.py`: load `ml/weights/best.pt`, preprocess (resize 640x640, CLAHE, color-space conversion), run detection, drop detections with `confidence < 0.4` (FR-006), assign crack severity low/medium/high from box size/aspect ratio (FR-007), and attach class weights `gamma_c`.

**Checkpoint**: Foundation ready - user stories can begin.

---

## Phase 3: User Story 1 - Safety-Aware Route Recommendation (Priority: P1) MVP

**Goal**: Fetch alternate routes, segment them, assess hazards, compute a 0-100 Safety Score, rank by safety+time, and recommend a route.

**Independent Test**: Submit a fixed origin/destination pair yielding 2+ alternatives; verify every route carries a Safety Score in [0,100] and a duration, and that a hazard-heavy route ranks below a comparable safer route.

### Tests for User Story 1

- [X] T014 [P] [US1] Unit test scoring math (`H_j = sum(gamma_c*w*p)`, `H = mean(H_j)`, `SafetyScore = 100*e^(-0.15H)` in [0,100], rank formula) in `backend/tests/unit/test_scoring.py`.
- [X] T015 [P] [US1] Unit test route segmentation (`N = ceil(d/L)`, ~equal lengths, midpoints within segment bounds) in `backend/tests/unit/test_segmentation.py`.
- [X] T016 [P] [US1] Contract test that `POST /api/route` response matches `contracts/openapi.yaml` `RouteResponse`/`Route` in `backend/tests/contract/test_route_contract.py`.
- [X] T017 [US1] Integration test with mocked routing + vision services covering recommend-one-route and graceful missing-image handling in `backend/tests/integration/test_route_flow.py`.

### Implementation for User Story 1

- [X] T018 [P] [US1] Create request/response validation helpers in `backend/api/schemas.py` (plain functions, no new dependency): require `origin`, `destination`; optional `preference`; clamp scores to [0,100].
- [X] T019 [US1] Implement `backend/services/routing.py`: geocode origin/destination, call Directions API with `alternatives=true`, decode polylines, return routes with `distance_m`, `duration_s`, `polyline` (research R1).
- [X] T020 [US1] Implement `backend/services/segmentation.py`: split each route polyline into segments of target `SEGMENT_LENGTH_M` (200-500 m), computing start/end/midpoint and `length_m`.
- [X] T021 [US1] Implement `backend/services/scoring.py`: per-segment hazard cost, route hazard cost, `SafetyScore = 100*e^(-lambda*H)` with `lambda=0.15`, and default ranking `Rank = 0.5*SafetyScore + 0.5*100*(t_min/t_i)` (default preference for US1).
- [X] T022 [US1] Implement `POST /api/route` in `backend/api/routes.py` orchestrating geocode -> routes -> segment -> imagery -> vision -> scoring -> rank -> recommend.
- [X] T023 [US1] Persist detections to the cache and append a `query_log` row via `backend/storage/db.py` (FR-017).
- [X] T024 [US1] Add input validation and upstream-failure handling to `POST /api/route` in `backend/api/routes.py` (unresolvable location -> 400; routing outage -> 502); missing-imagery handling superseded by T054 (FR-005, SC-008).
- [X] T025 [US1] Build `frontend/index.html`, `frontend/css/style.css`, `frontend/js/app.js`: origin/destination form, call `/api/route`, render the recommended route + all alternatives with Safety Scores and times on the Google Maps JS map.

**Checkpoint**: User Story 1 fully functional and independently testable (MVP).

---

## Phase 4: User Story 2 - Plain-Language Safety Preferences (Priority: P2)

**Goal**: Interpret a free-text preference into a safety/time weight and an avoid-class set, and use it in ranking.

**Independent Test**: Send the same trip with "take the safest route only" vs "fastest route, I'm in a hurry"; the recommendation shifts accordingly. Garbled/empty preference still returns a result (balanced default).

### Tests for User Story 2

- [X] T026 [P] [US2] Unit test preference parsing incl. invalid-JSON fallback (`alpha=0.5`, `avoidClasses=[]`, `interpreted=false`) in `backend/tests/unit/test_preference.py`.
- [X] T027 [P] [US2] Contract test for `preference`/`InterpretedPreference` (`alpha` in [0,1], `avoidClasses`, `interpreted`) in `backend/tests/contract/test_preference_contract.py`.

### Implementation for User Story 2

- [X] T028 [US2] Implement `ParsePreference` in `backend/services/llm.py`: prompt the LLM for strict JSON `{alpha, avoidClasses}`, validate; on invalid output or empty input fall back to `alpha=0.5`, `avoidClasses=[]`, `interpreted=false` (FR-010, FR-011, FR-015).
- [X] T029 [US2] Apply `avoidClasses` by boosting their `gamma_c` in `backend/services/scoring.py`, and accept `alpha` as the ranking weight (FR-012).
- [X] T030 [US2] Wire preference parsing into `POST /api/route` in `backend/api/routes.py` and return the `preference` object.
- [X] T031 [US2] Add a preference text input to `frontend/index.html` + `frontend/js/app.js` and send it in the request body.

**Checkpoint**: User Stories 1 and 2 both work independently.

---

## Phase 5: User Story 3 - Explained Recommendation (Priority: P3)

**Goal**: Generate a plain-language justification grounding the recommendation in the structured route data.

**Independent Test**: A request returns `explanation.generated=true` with text referencing the recommended route's time/safety vs at least one alternative; when the LLM fails, routes still return with `generated=false`.

### Tests for User Story 3

- [X] T032 [P] [US3] Unit test explanation grounding + LLM-failure degradation in `backend/tests/unit/test_explanation.py`.
- [X] T033 [P] [US3] Contract test for the `Explanation` object in `backend/tests/contract/test_explanation_contract.py`.

### Implementation for User Story 3

- [X] T034 [US3] Implement `Explain` in `backend/services/llm.py`: build a structured comparison (distance, time, hazard counts, Safety Score of the recommended route vs alternatives) and produce concise natural-language text (FR-013/FR-014, research R7).
- [X] T035 [US3] Call `Explain` from `POST /api/route` in `backend/api/routes.py`; on failure set `explanation.generated=false` and still return routes (research R9).
- [X] T036 [US3] Render the explanation in `frontend/js/app.js` + `frontend/css/style.css`.

**Checkpoint**: User Stories 1-3 independently functional.

---

## Phase 6: User Story 4 - Hazard Visibility on the Map (Priority: P4)

**Goal**: Show detected hazards with approximate locations and let users compare alternatives by Safety Score.

**Independent Test**: A completed recommendation displays the recommended route, its hazards with approximate locations, and the alternatives with their scores.

### Tests for User Story 4

- [X] T037 [P] [US4] Contract test for `GET /api/hazards?queryId=` returning `Hazard[]` in `backend/tests/contract/test_hazards_contract.py`.

### Implementation for User Story 4

- [X] T038 [US4] Ensure each route's `hazards` array includes `class`, `confidence`, `severity`, `lat`, `lng` in the `POST /api/route` response (`backend/services/scoring.py` / `backend/api/routes.py`).
- [X] T039 [US4] Implement `GET /api/hazards?queryId=` in `backend/api/routes.py` reading cached detections from `backend/storage/db.py` (404 when the query is unknown).
- [X] T040 [US4] Add hazard markers and an alternatives comparison panel to `frontend/js/app.js` + `frontend/css/style.css`.

**Checkpoint**: All four user stories independently functional.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T041 [P] Input validation/security hardening: keep all API keys server-side, validate and bound all request fields in `backend/api/schemas.py`.
- [X] T042 [P] Reuse cached detections in `backend/services/vision.py` + `backend/storage/db.py` to avoid re-running inference on repeated segments.
- [X] T043 [P] Add request timing/latency logging for the recommendation path in `backend/app.py`.
- [X] T044 Run `specs/001-safe-route-navigation/quickstart.md` validation scenarios end-to-end against the served `backend/app.py` and fix gaps.
- [X] T045 [P] Update `README.md` with final configuration and the automated test commands.

---

## Phase 8: Clarification Deltas (FR-018..FR-020, SC-001, SC-009..SC-011)

**Goal**: Bring the implementation in line with the clarification session: coverage-aware scoring (only assessed segments), imagery staleness exclusion, unassessed routes never outranking assessed ones, 30-day log retention, and the quantified latency target.

**Independent Test**: Remove all imagery for one candidate route; verify that route reports `assessed=false` and `imageryCoverage=0`, is not recommended over an assessed route, that stale imagery is excluded from scoring, and that expired query logs are deleted.

### Tests for Clarification Deltas

- [X] T046 [P] Unit test coverage-aware scoring (average over assessed segments only; zero assessed segments -> `assessed=false`) in `backend/tests/unit/test_scoring.py`.
- [X] T047 [P] Unit test staleness (image with `captured_at` older than `IMAGERY_STALENESS_DAYS` is treated as stale/unassessed) in `backend/tests/unit/test_imagery.py`.
- [X] T048 [P] Unit test log retention (rows older than `LOG_RETENTION_DAYS` deleted by the purge) in `backend/tests/unit/test_retention.py`.
- [X] T049 [P] Contract test that each route includes `assessedSegments`, `totalSegments`, `imageryCoverage` (0-1), and `assessed` per `contracts/openapi.yaml` in `backend/tests/contract/test_route_contract.py`.
- [X] T050 Integration test that a fully unassessed route (`assessed=false`) is never recommended over an assessed route in `backend/tests/integration/test_route_flow.py`.

### Implementation for Clarification Deltas

- [X] T051 [P] Add `IMAGERY_STALENESS_DAYS=180` and `LOG_RETENTION_DAYS=30` (env-overridable) to `backend/config.py`.
- [X] T052 Update `backend/services/scoring.py`: `route_hazard_cost` averages assessed-segment costs only; add a helper returning `imagery_coverage` (assessed/total) and the `assessed` flag.
- [X] T053 Update `backend/services/imagery.py`: exclude images whose `captured_at` is older than `IMAGERY_STALENESS_DAYS`; treat images without `captured_at` as unassessed (FR-018).
- [X] T054 Update `_assess_route` in `backend/api/routes.py` to track `assessedSegments`/`totalSegments`, exclude unassessed segments from the average, and serialize `assessedSegments`, `totalSegments`, `imageryCoverage`, `assessed` (FR-019).
- [X] T055 Update ranking in `backend/api/routes.py` so a route with `assessed=false` is never recommended over an assessed route (FR-019).
- [X] T056 Add query-log purge in `backend/storage/db.py` (delete rows older than `LOG_RETENTION_DAYS`) and invoke it on init and on each new query log (FR-020).
- [X] T057 Ensure `origin_text`/`dest_text`/`preference_text` are treated as personal data — not written to stdout logs or returned by any endpoint beyond the request response — in `backend/api/routes.py` + `backend/app.py` (FR-020).
- [X] T058 [P] Display imagery coverage and a "partially assessed" / "unassessed" badge in `frontend/js/app.js` + `frontend/css/style.css` (SC-009).
- [X] T059 [P] Update `README.md` and `specs/001-safe-route-navigation/quickstart.md` for the new `IMAGERY_STALENESS_DAYS` and `LOG_RETENTION_DAYS` variables.

**Checkpoint**: Implementation matches the clarified spec (FR-018..FR-020, SC-009..SC-011) and the quantified latency target.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories.
- **User Stories (Phase 3-6)**: All depend on Foundational.
- **Polish (Phase 7)**: Depends on the desired user stories being complete.
- **Clarification Deltas (Phase 8)**: Depends on Phase 7; re-aligns the implementation with the clarified spec.

### User Story Dependencies

- **US1 (P1)**: Starts after Foundational; no dependency on other stories.
- **US2 (P2)**: Starts after Foundational; extends scoring/ranking from US1 (integration point T029).
- **US3 (P3)**: Starts after Foundational; consumes US1 route data (integration point T035).
- **US4 (P4)**: Starts after Foundational; consumes US1 hazard data (integration point T038/T039).

### Within Each Story

- Tests first, then models/schemas, services, endpoints, frontend.
- Core implementation before integration.

### Parallel Opportunities

- Setup: T002, T003, T004 in parallel.
- Foundational: T007, T010 in parallel; T005 before T006/T023.
- US1: tests T014, T015, T016 in parallel; T018 parallel with tests.
- US2: T026, T027 in parallel.
- US3: T032, T033 in parallel.
- US4: T037 parallel with T038.
- Deltas: tests T046, T047, T048, T049 in parallel; T051/T058/T059 in parallel; T052 before T054; T054 before T055.

## Parallel Example: User Story 1

```bash
Task: "Unit test scoring math in backend/tests/unit/test_scoring.py"
Task: "Unit test segmentation in backend/tests/unit/test_segmentation.py"
Task: "Contract test POST /api/route in backend/tests/contract/test_route_contract.py"
```

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1 Setup -> 2. Phase 2 Foundational -> 3. Phase 3 US1 -> **STOP and validate US1** -> demo.

### Incremental Delivery

1. Setup + Foundational -> foundation ready.
2. US1 -> test -> demo (MVP).
3. US2 -> test -> demo. 4. US3 -> test -> demo. 5. US4 -> test -> demo.
Each story adds value without breaking earlier ones.

## Notes

- [P] = different files, no dependencies.
- Verify tests fail before implementing.
- Commit after each task or logical group.
- Commit `ml/weights/best.pt` is intentionally git-ignored (regenerate via T011).
