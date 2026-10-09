# Phase 0 Research: SafeRoute AI

All NEEDS CLARIFICATION items from the Technical Context are resolved below.

## R1. Routing and geocoding provider

- **Decision**: Use the Google Maps Directions API (`alternatives=true`) for candidate
  routes and the Google Maps Geocoding API to resolve free-text origin/destination to
  coordinates. Decode route geometry with a standard polyline decoder.
- **Rationale**: The feature and source paper are built around Google Maps; it returns
  multiple alternatives with distance/duration and encoded polylines in one call.
- **Alternatives considered**: OpenRouteService / OSRM (open, no quota cost) — viable
  fallback, but weaker global geocoding. Kept as a future swap behind `services/routing.py`.

## R2. Hazard detection model and dataset

- **Decision**: Fine-tune YOLOv8 (Ultralytics) from COCO-pretrained weights on RDD2020
  plus additional images for the `waterlogging` and `uneven/subsided surface` classes.
  Five detection classes: pothole, crack, damaged patch, waterlogging, uneven surface.
- **Rationale**: YOLOv8 balances accuracy and latency, runs on CPU, and Ultralytics
  provides a simple train/export path. RDD2020 is the established multi-class road
  damage benchmark and includes Indian imagery.
- **Alternatives considered**: YOLOv7 (older), segmentation models (BARNet/U-Net-like)
  for cracks — rejected as the primary detector for latency/complexity; crack
  *severity* is handled separately (R3).

## R3. Crack severity estimation

- **Decision**: A lightweight severity classifier (low/medium/high) driven by crack
  size and aspect ratio over the detected region, applied after detection. Severity
  maps to weight `w` in {1,2,3}.
- **Rationale**: Spec requires severity to influence the hazard cost. Full pixel-level
  segmentation is heavier than needed for a prototype.
- **Alternatives considered**: Pixel-segmentation network for severity — deferred; the
  box-based heuristic is adequate and swappable.

## R4. Segment imagery source

- **Decision**: For each segment midpoint, look up the nearest road image in the local
  imagery store by geo-proximity; images carry location + capture-time metadata.
- **Rationale**: Spec/assets assume a pre-existing dataset; no live capture in v1.
  Metadata supports the "stale imagery" limitation and future freshness filtering.
- **Alternatives considered**: Street View Static API for on-demand imagery — rejected
  for v1 due to per-request cost/quota and coverage gaps; noted as future enhancement.

## R5. Safety Score formula and constants

- **Decision**: Per-segment hazard cost `H_j = Σ γ_c · w · p` over detections above
  confidence threshold τ=0.4; route cost `H = (1/N) Σ H_j`; `SafetyScore = 100·e^(−λH)`
  with λ=0.15 and class weights γ_c. Constants live in `config.py`.
- **Rationale**: Matches the spec/published method. Exponential mapping bounds the
  score to (0,100] and is monotonic in hazard cost.
- **Alternatives considered**: Linear penalty — rejected (unbounded, poor dynamic
  range). Note: constants are prototype values, not validated against accident data.

## R6. Ranking / preference weighting

- **Decision**: `Rank = α·SafetyScore + (1−α)·100·(t_min / t_i)`, where α∈[0,1] is the
  safety-vs-time weight interpreted from the user's preference and `t_min` is the
  fastest candidate duration. Avoided hazard classes increase their γ_c penalty.
- **Rationale**: Bias-free combination of two 0-100 terms; time term normalized to the
  best available candidate. Default α=0.5 when no valid preference.
- **Alternatives considered**: Weighted sum of raw seconds (units mismatch) — rejected.

## R7. LLM provider and output handling

- **Decision**: A hosted chat/completion LLM API accessed via `services/llm.py`, with
  the model constrained to strict JSON for preference parsing (schema: `alpha`,
  `avoidClasses`). Explanation is generated text grounded in structured route data.
  Provider endpoint/key/model supplied via environment config, so the provider is
  swappable without code changes.
- **Rationale**: JSON-schema-constrained output reduces hallucination and makes parsing
  deterministic; environment config avoids hard-coding a vendor.
- **Alternatives considered**: Prompt-only free text + regex parsing (fragile) —
  rejected; local open-weight LLM (higher ops cost for a prototype) — deferred.

## R8. Preference fallback

- **Decision**: If the LLM returns invalid/unparseable JSON, or preference is empty,
  use α=0.5 and an empty avoid-set, and continue.
- **Rationale**: Directly required by FR-015 / Algorithm 2; guarantees a result.

## R9. External failure handling

- **Decision**: Each external call (routing, LLM, imagery) is wrapped with timeout and
  a defined fallback: routing failure → error to user with retry; missing imagery for a
  segment → segment is **excluded** from the hazard-cost average (not counted as
  neutral); LLM explanation failure → return routes without explanation rather than
  failing the request.
- **Rationale**: SC-008 requires graceful degradation. Keeps trust boundaries explicit.
  Aligned with clarified FR-019 (score only over assessed segments).

## R10. Caching and persistence

- **Decision**: SQLite tables cache hazard detections keyed by image id, and log query
  requests/results. Image metadata (location, capture time) is indexed for proximity
  lookup.
- **Rationale**: Avoids re-running inference on repeated segments; supports analysis.
- **Alternatives considered**: MySQL — deferred (spec says "eventually MySQL"); SQLite
  is sufficient at prototype scale.

## R11. Testing approach

- **Decision**: pytest. Unit tests for scoring, segmentation, and preference fallback;
  integration tests with recorded/mocked routing + LLM responses; contract tests
  validating the REST API shape. Vision inference tested on a small fixed image set.
- **Rationale**: External services are non-deterministic and cost money, so they are
  mocked at the boundary; scoring math is pure and fully unit-testable.

## R12. Coverage-aware scoring (FR-019)

- **Decision**: Route hazard cost `H_i` averages the per-segment costs of *assessed*
  segments only; unassessed segments (no usable imagery) are excluded. Each route
  reports `assessedSegments` and `totalSegments`; a route with zero assessed segments
  is marked `assessed=false` and is never recommended over an assessed route (unless
  no assessed route exists).
- **Rationale**: Prevents an un-assessed route from being portrayed as perfectly safe
  (a 100 score built on no evidence). Matches clarified FR-019/SC-009.
- **Alternatives considered**: Treat missing as neutral (rejected — misleading) or as
  maximum risk (rejected — over-penalizes unknown roads).

## R13. Imagery staleness (FR-018)

- **Decision**: A configurable cutoff `IMAGERY_STALENESS_DAYS` (default 180) marks
  imagery as stale. Stale imagery is excluded from hazard scoring and reduces reported
  coverage. `captured_at` is required for this to apply; imagery without it is treated
  as unassessed.
- **Rationale**: Makes the "stale imagery" limitation enforceable and testable rather
  than advisory. Matches clarified FR-018/SC-011.

## R14. Log retention and privacy (FR-020)

- **Decision**: Query logs (origin, destination, preference text) are retained for a
  maximum of `LOG_RETENTION_DAYS=30` and deleted thereafter by a lightweight purge on
  startup/query. This data is treated as personal data and only shared with the routing
  and LLM services needed to fulfill the request.
- **Rationale**: Bounds exposure of location history while keeping short-term analysis.
  Matches clarified FR-020/SC-010.
- **Alternatives considered**: Retain indefinitely (rejected — privacy risk); store no
  raw text (rejected — loses analysis value and query replay).

## R15. Latency target (SC-001)

- **Decision**: Target p95 end-to-end latency under 45 s for trips up to 20 km with up
  to 3 alternatives, achieved via detection caching, capped alternatives, and batching.
- **Rationale**: Realistic for CPU per-segment inference plus one LLM call; gives an
  objective pass/fail for SC-001.

## Resolved unknowns summary

| Unknown | Resolution |
|---------|------------|
| Routing provider | Google Maps Directions + Geocoding, fallback OSRM |
| Detector + dataset | YOLOv8 fine-tuned on RDD2020 + extra classes |
| Severity | Box-size/aspect-ratio heuristic classifier |
| Imagery | Geo-proximity lookup in local image store |
| Score/ranking | Documented formulas with prototype constants in config |
| LLM | Swappable chat/completion API, strict JSON, env-configured |
| Failures | Timeouts + defined fallbacks (degrade, don't fail) |
| Storage | SQLite cache + query log |
| Missing imagery | Excluded from average; route reports coverage; unassessed never outranks assessed |
| Stale imagery | Older than 180 days excluded from scoring; reduces coverage |
| Log retention | 30 days, treated as personal data |
| Latency target | p95 < 45 s for <=20 km / <=3 alternatives |
