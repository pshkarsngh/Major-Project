# Phase 1 Data Model: SafeRoute AI

Entities derive from the feature spec (Key Entities). Storage is SQLite for cached
results and logs; routes/segments are computed per request and only their detections
and logs are persisted.

## Route

A candidate path between origin and destination.

| Field | Type | Notes |
|-------|------|-------|
| id | string | Stable id within a request (e.g., `r1`) |
| distance_m | integer | Total length |
| duration_s | integer | Travel time without traffic-adjusted realism claims |
| polyline | string | Encoded geometry from routing service |
| safety_score | float | 0-100, computed over assessed segments only |
| rank | float | Combined ranking value |
| recommended | boolean | True for the selected route |
| assessed_segments | integer | Segments with usable (non-stale) imagery |
| total_segments | integer | All segments in the route |
| imagery_coverage | float | assessed_segments / total_segments (0-1) |
| assessed | boolean | False when assessed_segments = 0 |

**Relationships**: has many Segments; belongs to one QueryLog entry.

**Validation**: `safety_score` must be within [0, 100]; `distance_m` > 0;
`duration_s` > 0; a route with `assessed=false` MUST NOT be recommended over an
assessed route unless no assessed route exists (FR-019).

## Segment

A contiguous, approximately equal-length portion of a route.

| Field | Type | Notes |
|-------|------|-------|
| route_id | string | Parent route |
| index | integer | Position along the route |
| start_lat, start_lng | float | Segment start |
| end_lat, end_lng | float | Segment end |
| midpoint_lat, midpoint_lng | float | Used for imagery lookup |
| length_m | integer | Target 200-500 m |
| hazard_cost | float | Computed from detections |

**Relationships**: belongs to one Route; has zero or more HazardDetections; maps to
zero or one RoadImage.

**Validation**: segment lengths should approximate the target L; midpoint must fall
within the segment bounds.

## RoadImage

A stored image associated with a location, used as evidence for a segment.

| Field | Type | Notes |
|-------|------|-------|
| id | integer | Primary key |
| file_path | string | Location on disk |
| lat, lng | float | Capture location |
| captured_at | datetime | Capture time (supports staleness assessment) |

**Relationships**: may produce many HazardDetections (cached by image id).

**Validation**: `lat`/`lng` required; `captured_at` required to apply staleness — an
image with `captured_at` older than the staleness cutoff (default 180 days) is treated
as stale and excluded from scoring (FR-018).

## HazardDetection

A detected road defect within a segment/image.

| Field | Type | Notes |
|-------|------|-------|
| id | integer | Primary key |
| image_id | integer | Source image (for cache reuse) |
| segment_index | integer | Segment it falls in |
| hazard_class | enum | pothole, crack, damaged_patch, waterlogging, uneven_surface |
| confidence | float | 0-1 |
| bbox | string/JSON | Bounding box extent |
| severity | enum | low, medium, high (crack severity; default low others) |
| class_weight | float | γ_c for the class |

**Relationships**: belongs to a Segment (by index) and a RoadImage.

**Validation**: detections with `confidence < τ` (default 0.4) are discarded (FR-006);
`hazard_class` must be one of the five classes.

## UserPreference

Interpreted representation of the user's stated intent.

| Field | Type | Notes |
|-------|------|-------|
| raw_text | string | Original user input (may be empty) |
| alpha | float | Safety weight in [0,1] |
| avoid_classes | list<enum> | Hazard classes to penalize more |
| interpreted | boolean | False when fallback default applied |

**Relationships**: applies to one QueryLog entry.

**Validation**: `alpha` clamped to [0,1]; on invalid interpretation
`alpha=0.5`, `avoid_classes=[]`, `interpreted=false` (FR-015).

## SafetyScore

A normalized 0-100 measure of route road quality.

| Field | Type | Notes |
|-------|------|-------|
| route_id | string | Owning route |
| value | float | 100·e^(−λH), H averaged over assessed segments only |
| hazard_cost | float | Route-level H (assessed segments) |

**Validation**: `value` within [0, 100]; higher means safer (FR-009); undefined when
there are zero assessed segments (route marked `assessed=false`).

## Explanation

Plain-language justification for the recommendation.

| Field | Type | Notes |
|-------|------|-------|
| route_id | string | Recommended route |
| text | string | Natural-language justification |
| generated | boolean | False when LLM failed (degrade without failing) |

**Validation**: must reference recommended route's time/safety vs at least one
alternative when `generated=true` (FR-014).

## QueryLog

A record of a past route request and its outcome.

| Field | Type | Notes |
|-------|------|-------|
| id | integer | Primary key |
| origin_text, dest_text | string | User input |
| preference_text | string | Optional |
| created_at | datetime | Timestamp |
| recommended_route_id | string | Selected route |
| result_summary | JSON | Routes, scores, hazards |

**Validation**: append-only; rows older than the retention window (default 30 days)
are deleted, and `origin_text`/`dest_text`/`preference_text` are treated as personal
data (FR-020).

## State Transitions

Request lifecycle (per query):

```text
received -> routes_retrieved -> segmented -> assessed -> scored -> ranked
         -> explained -> returned
```

Degraded branches (do not abort the request):
- no usable image for a segment (missing or stale) -> segment excluded from the hazard-cost average and coverage reduced (FR-018/FR-019)
- LLM explanation fails -> `explanation.generated = false`, routes still returned
- preference parse fails -> default preference, `interpreted = false`
