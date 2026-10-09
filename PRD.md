# PRD: SafeRoute AI - Safety-Aware Navigation

**Status**: Draft
**Date**: 2026-10-09
**Owner**: SafeRoute AI team
**Related docs**: `specs/001-safe-route-navigation/spec.md` (detailed spec), `plan.md`, `tasks.md`

## 1. Overview

SafeRoute AI is a web navigation tool that recommends the safest driving route
between two points, not just the fastest. It detects road hazards from imagery,
turns them into a 0-100 Safety Score per route, factors in travel time, and explains
the recommendation in plain language.

## 2. Problem

Conventional navigation (e.g., Google Maps) optimizes time and distance, implicitly
assuming every kilometer carries equal risk. In India, potholes, cracks, waterlogging,
and broken surfaces are exactly what commuters care about, yet they are ignored.
A two-wheeler and a car on the same pothole-ridden road face very different risks.
And even when risk data exists, the recommendation is a black box - the user is not
told why one route is preferred.

## 3. Goals

- Rank candidate routes using hazard-aware Safety Scores combined with travel time.
- Detect multiple hazard classes (potholes, cracks, damaged patches, waterlogging,
  uneven/subsided surfaces) from road imagery.
- Let users state preferences in natural language (e.g., "avoid potholes", "safest
  route only").
- Explain the recommended route in plain language.
- Deliver a working end-to-end prototype (backend + hazard detection + web frontend).

## 4. Non-Goals (this version)

- Real-time image capture or live camera feeds.
- Crowdsourced reporting, drone/satellite imagery, or V2X integration.
- Accident-probability prediction (the Safety Score is a relative risk measure only).
- Native mobile apps, user accounts, and multi-city scale.

## 5. Target Users

- **Daily commuters** (especially two-wheeler riders) who want a less punishing ride.
- **Ride-hailing / last-mile delivery drivers** wanting to reduce vehicle damage.
- **Elderly and cautious drivers** prioritizing comfort and safety over speed.

## 6. Key Use Cases

1. User enters origin and destination; sees all routes with Safety Scores and times;
   gets a recommended route.
2. User adds a preference like "avoid potholes, I'm not in a hurry"; ranking adjusts.
3. User reads a plain-language explanation of why the route was chosen.
4. User views the route, detected hazards with approximate locations, and alternatives
   on a map.

## 7. Functional Requirements (summary)

Full, testable list: see `spec.md` FR-001..FR-018. Product-level summary:

- Retrieve multiple candidate routes between origin and destination.
- Split each route into ~200-500 m segments and assess hazards per segment from imagery.
- Detect five hazard classes; assign severity; ignore low-confidence detections.
- Compute a 0-100 Safety Score per route (higher is safer).
- Interpret optional natural-language preferences into a safety/time weight and an
  avoid-class set; fall back to a balanced default when unparseable.
- Rank routes by Safety Score + travel time and recommend the top one.
- Return a plain-language explanation; degrade gracefully if explanation fails.
- Present route, hazards, and alternatives on a map.
- Persist detections and query logs; keep imagery location/capture-time metadata.

## 8. UX Flow

```
Origin + Destination (+ optional preference)
  -> Loading
  -> Results: recommended route on map, Safety Score, travel time,
     detected hazards, explanation, ranked alternatives
```

## 9. Success Metrics

- Every returned route shows a Safety Score in [0,100]; exactly one is recommended.
- At least five hazard classes recognized.
- Preference-driven ranking shifts in the stated direction in >=80% of test cases.
- When a hazard-free route and a comparable hazard-heavy route exist, the safer route
  is recommended in >=80% of test cases.
- Missing imagery or LLM failure never fails the request (graceful degradation).
- Recommendation for a typical trip returns in a single request within an acceptable
  interactive time (target < ~45 s at prototype scale).

## 10. Assumptions & Constraints

- Access to a routing/geocoding service returning alternatives.
- A pre-existing annotated road-image dataset (RDD2020 + extra classes) with location
  and capture-time metadata; imagery may be stale.
- Safety Score weights and the decay factor are prototype values, not validated
  against accident data.
- External API quotas/cost and LLM hallucination risk are managed via schema-validated
  outputs and server-side keys.

## 11. Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Stale imagery misrepresents current road conditions | Inaccurate scores | Capture-time metadata; future crowdsourcing/live feeds |
| Hazard detector generalization to new geographies | Missed/false hazards | Report precision/recall/mAP; expand training data |
| LLM produces unusable output | Broken parse/explanation | Strict JSON schema + balanced fallback + degrade explanation |
| Per-segment inference latency/cost | Slow or expensive requests | Cache detections; cap alternatives; batch inference |
| Unvalidated Safety Score constants | Over-trust in the score | Label as relative risk; calibrate with real data later |

## 12. Milestones

1. **Foundation**: project structure, storage, Flask skeleton, health check, trained model.
2. **MVP (US1)**: safety-aware route recommendation end-to-end.
3. **US2**: natural-language preferences.
4. **US3**: explained recommendation.
5. **US4**: hazard visibility on the map.
6. **Polish**: caching, security, docs, quickstart validation.

## 13. Out of Scope / Future

Live municipal camera feeds, drone and satellite imagery, crowdsourced hazard
reporting, V2X alerts, and Smart City maintenance integration are future scope.
