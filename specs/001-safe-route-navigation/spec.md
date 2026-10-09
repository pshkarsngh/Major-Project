# Feature Specification: SafeRoute AI - Safety-Aware Navigation

**Feature Branch**: `001-safe-route-navigation`

**Created**: 2026-10-09

**Status**: Draft

**Input**: User description: "SafeRoute AI: Intelligent Road Safety Navigation System Using Computer Vision, Large Language Models, and Google Maps API. A navigation system that detects road hazards from imagery and ranks routes by safety, interprets plain-language safety preferences, and explains the recommended route."

## Clarifications

### Session 2026-10-09

- Q: When no road imagery is available for some or all segments of a route, how should that route be scored and presented? → A: Exclude unassessed segments from the route average and compute the Safety Score only over assessed segments; report imagery coverage and mark routes with no assessed segments as unassessed.
- Q: Should users be able to specify a transport or vehicle type (e.g., two-wheeler vs car) that changes how hazards are weighted and ranked? → A: Out of scope for v1; a single risk profile is used for all users.
- Q: How long should persisted query logs (origin, destination, and preference text) be retained, and should they be treated as personal data? → A: Retain for a fixed 30-day window then delete; treat location and preference text as personal data.
- Q: What end-to-end response-time target must a route recommendation meet under normal conditions? → A: p95 under ~45 seconds for trips up to ~20 km with up to 3 alternatives.
- Q: What makes road imagery "stale," and what should the system do with stale imagery? → A: Imagery older than a configurable cutoff (default 180 days) is stale and is excluded from hazard scoring, with the reduced coverage reported.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Safety-Aware Route Recommendation (Priority: P1)

A commuter enters an origin and destination. The system returns several candidate
routes, each annotated with a Safety Score that reflects the road hazards found
along it, and recommends the route that best balances safety against travel time.
Instead of only being offered the fastest route, the commuter can see which route
has fewer or less severe road defects.

**Why this priority**: This is the core value of the product. Without hazard-aware
scoring and ranking, the system is indistinguishable from conventional navigation.
It is a complete, demonstrable slice on its own.

**Independent Test**: Submit a fixed origin/destination pair that yields at least two
alternatives, then verify that every returned route carries a Safety Score and a
travel time, and that a route with more/severer hazards is ranked below a
comparably long route with fewer/less severe hazards.

**Acceptance Scenarios**:

1. **Given** a valid origin and destination with multiple available routes, **When** the user requests navigation, **Then** the system returns all candidate routes, each showing a Safety Score between 0 and 100 and a travel time, plus one recommended route.
2. **Given** two routes of similar length where one contains significantly more or severer hazards, **When** routes are ranked, **Then** the safer route receives the higher rank.
3. **Given** a route whose segments contain no detected hazards, **When** its score is computed, **Then** its Safety Score is higher than any route containing detected hazards.

---

### User Story 2 - Plain-Language Safety Preferences (Priority: P2)

A commuter expresses a preference in everyday language, such as "avoid potholes" or
"take the safest route only" or "I'm in a hurry." The system interprets the intent
and adjusts how strongly safety versus travel time influences the recommendation and
which hazard types to penalize.

**Why this priority**: Adds meaningful personalization and removes the need for
technical settings, but the product still works without it (defaulting to a balanced
preference).

**Independent Test**: Submit the same origin/destination with different preference
phrases and verify the ranking changes consistently with the stated intent (e.g.,
"safest route only" favors safety, "fastest" favors time).

**Acceptance Scenarios**:

1. **Given** a preference such as "avoid potholes," **When** routes are ranked, **Then** routes with potholes are penalized more than routes without, relative to the default.
2. **Given** a preference such as "take the safest route only," **When** routes are ranked, **Then** safety dominates travel time in the ranking.
3. **Given** an uninterpretable or empty preference, **When** routes are ranked, **Then** the system applies a balanced default and continues normally.

---

### User Story 3 - Explained Recommendation (Priority: P3)

After recommending a route, the system explains in plain language why it was chosen,
referencing the trade-off (for example, extra minutes versus fewer potholes) and the
detected hazards avoided.

**Why this priority**: Builds trust and differentiates the system from a black-box
score, but the recommendation itself is useful without the explanation.

**Independent Test**: Request navigation and verify the response includes a
human-readable justification that references the recommended route's time and
safety relative to at least one alternative.

**Acceptance Scenarios**:

1. **Given** a recommended route and at least one alternative, **When** the result is presented, **Then** a plain-language explanation is shown that references the safety/time trade-off.
2. **Given** the recommended route has detected hazards, **When** the explanation is generated, **Then** the explanation reflects the actual hazards and scores rather than generic text.

---

### User Story 4 - Hazard Visibility on the Map (Priority: P4)

A commuter views the recommended route on a map alongside the detected hazards and
their approximate locations, and can compare alternatives by their Safety Scores.

**Why this priority**: Improves transparency and trust but is not required for the
core recommendation to work.

**Independent Test**: Request navigation and verify the map displays the recommended
route, its hazards with approximate locations, and the alternative routes with scores.

**Acceptance Scenarios**:

1. **Given** a completed recommendation, **When** the results are displayed, **Then** the recommended route, its detected hazards with approximate locations, and the alternatives with their Safety Scores are all visible.

---

### Edge Cases

- What happens when the routing service returns only a single route (no alternatives)?
- What happens when no road imagery is available for some or all segments of a route?
- What happens when the preference text cannot be interpreted or the interpretation output is malformed?
- What happens when the destination is unreachable or an origin/destination cannot be resolved?
- What happens when all candidate routes have identical Safety Scores and travel times?
- How does the system behave when an external dependency (routing, imagery, or language service) is temporarily unavailable?
- How does the system handle very long routes that produce a large number of segments?
- What happens when road imagery is stale and no longer reflects current conditions?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Users MUST be able to specify an origin and a destination for a route request.
- **FR-002**: System MUST retrieve multiple candidate routes between the origin and destination, each with a total distance and travel time.
- **FR-003**: System MUST divide each candidate route into contiguous segments of approximately equal length (target 200-500 m, adapted to area density).
- **FR-004**: System MUST assess each segment for road hazards across multiple classes: potholes, cracks, damaged patches, waterlogging, and uneven/subsided surfaces.
- **FR-005**: System MUST derive hazard assessments from road imagery associated with each segment.
- **FR-006**: System MUST discard hazard detections whose confidence is below a configurable threshold.
- **FR-007**: System MUST assign a severity level (low, medium, high) to detected hazards.
- **FR-008**: System MUST compute a per-segment hazard cost from the count, severity, confidence, and class weight of detected hazards.
- **FR-009**: System MUST aggregate per-segment costs into a route-level Safety Score normalized to 0-100, where higher means safer.
- **FR-010**: Users MUST be able to provide an optional safety preference in natural language.
- **FR-011**: System MUST interpret a natural-language preference into a safety-versus-time weighting and a set of hazard classes to avoid.
- **FR-012**: System MUST rank candidate routes by combining the Safety Score and travel time according to the interpreted preference.
- **FR-013**: System MUST recommend the highest-ranked route.
- **FR-014**: System MUST produce a plain-language explanation of the recommendation that references the recommended route's safety and time relative to at least one alternative.
- **FR-015**: System MUST fall back to a balanced default preference (equal safety/time weight, no avoided classes) when a preference is absent or cannot be interpreted.
- **FR-016**: System MUST present the recommended route and alternatives with their Safety Scores, travel times, and detected hazards with approximate locations.
- **FR-017**: System MUST persist hazard detection results and query logs to support reuse, caching, and later analysis.
- **FR-018**: System MUST record location and capture-time metadata for road imagery and MUST treat imagery older than a configurable staleness threshold (default 180 days) as stale, excluding stale imagery from hazard scoring and reflecting the resulting reduced coverage (per FR-019).
- **FR-019**: System MUST compute each route's Safety Score over only those segments for which imagery was available, excluding unassessed segments from the hazard-cost average, and MUST report imagery coverage; a route with no assessed segments MUST be marked as unassessed and MUST NOT be recommended over an assessed route unless no assessed route exists.
- **FR-020**: System MUST retain query logs (origin, destination, and preference text) for a maximum of 30 days and delete them thereafter, and MUST treat this data as personal data (not shared with third parties beyond the routing/LLM services required to fulfill the request).

### Key Entities *(include if data involved)*

- **Route**: A candidate path between origin and destination; attributes include distance, travel time, geometry, and computed Safety Score.
- **Segment**: A contiguous portion of a route of approximately equal length; the unit at which hazards are assessed.
- **Road Image**: An image associated with a segment's location; attributes include location and capture time.
- **Hazard Detection**: A detected road defect within a segment; attributes include hazard class, confidence, bounding extent, and severity.
- **Safety Score**: A normalized 0-100 measure of a route's road quality derived from its hazard detections.
- **User Preference**: An interpreted representation of the user's stated intent; attributes include safety-versus-time weighting and the set of hazard classes to avoid.
- **Explanation**: A plain-language justification for the recommended route.
- **Query Log**: A record of past route requests and results.
- **Road Image Cache**: Stored hazard detection results keyed by imagery so repeated assessments are avoided.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can obtain a safety-aware route recommendation from a valid origin/destination pair in a single request, with p95 end-to-end latency under 45 seconds for trips up to 20 km with up to 3 alternatives.
- **SC-002**: 100% of returned candidate routes display a Safety Score within the 0-100 range.
- **SC-003**: The system recognizes at least five distinct road hazard classes.
- **SC-004**: In the absence of a preference, the system applies a balanced default and still returns a recommendation 100% of the time.
- **SC-005**: For requests where preferences are given, the resulting ranking shifts in the stated direction (toward safety or toward time) in at least 80% of test cases.
- **SC-006**: Every recommendation is accompanied by a plain-language explanation that cites the recommended route's time and safety relative to at least one alternative.
- **SC-007**: When a hazard-bearing route and a hazard-free route of comparable length are both available, the system recommends the hazard-free route in at least 80% of test cases.
- **SC-008**: Uninterpretable preferences or missing imagery do not cause request failure; the system degrades gracefully and still returns a result.
- **SC-009**: Every route response reports imagery coverage; routes with no assessed segments are marked as unassessed and are not recommended over assessed routes.
- **SC-010**: Query logs older than 30 days are deleted; origin/destination/preference text is stored and handled as personal data.
- **SC-011**: Imagery older than the staleness threshold is not used for hazard scoring, and the excluded segments are reflected in the reported coverage.

## Assumptions

- The system has access to a routing/geocoding service that can return multiple alternative routes between two points.
- A pre-existing annotated road-image dataset is available for training and for segment-level lookup, with location and capture-time metadata.
- Road imagery may be stale; real-time image acquisition is out of scope for this version (a known limitation).
- Hazard detection quality is bounded by the training data and may not generalize to unseen geographies.
- Safety Score weights and the decay factor are prototype values that express relative risk, not statistically validated accident probabilities.
- Users have internet connectivity to reach external routing and language services.
- The initial version targets a single-user web experience; multi-user scale, authentication, and mobile apps are out of scope.
- A single risk profile is used for all users; per-vehicle-type hazard weighting (e.g., two-wheeler vs car) is out of scope for this version.
- Live municipal camera feeds, drone/satellite imagery, crowdsourcing, and vehicle-to-infrastructure communication are future scope, not part of this version.
