# Feature Specification: Agent-Based Area Search for Direct Journeys

**Feature Branch**: `012-agent-based-search`

**Created**: 2026-11-01

**Status**: Draft

**Input**: User description: "Feature 012: agent-based area search for direct journeys. Passenger asks area to area, e.g. Aluva to Kaloor where Kaloor has K1/K2 opposite sides plus K3 walkable in kaloor#1 and K4/K5 far in kaloor#2. What changes: agent resolves groups first via search_places, tests all member pairs via find_routes_matrix with pos_from < pos_to, classifies per route as direct exact stop plus nearby walkable mates where d <= 150m, answers per route with /routes/:id evidence plus walk distance note. Ask map/list pick only after tools find nothing viable. Same flow symmetrically for origin ambiguity. Why: exact-id refuse on wrong side forces needless picks though crossing road suffices. Out of scope: far-group onward routing and shared-location origin, but add nearby_stops tool now for next feature."

## Clarifications

### Session 2026-11-01

- Q: When the pair test finds no viable direct route, should the helper refuse outright or offer the map/list pick? → A: Offer the pick only when pairs went untested (pair-cap truncation) or the place never matched; refuse politely otherwise.
- Q: How should the helper decide which place groups count as "near" and get tested first? → A: Minimum member-to-member stop distance across the two ends, nearest first; truncate farthest pairs first under the cap.
- Q: When several routes serve the tested pairs, how many should the answer cite and in what order? → A: At most 5 destinations, ranked by operator group, then stop count, then route id.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Area-to-area question answered without a forced pick (Priority: P1)

A passenger asks how to get from one area to another, for example "Aluva to Kaloor". The destination has several same-named stops: K1/K2 on opposite sides of the road plus a walkable K3 in one cluster (kaloor#1), and far-away K4/K5 in a second cluster (kaloor#2). The journey helper resolves both areas to their place groups first, tests every member-stop pair for a direct route, and answers with the route, the exact boarding and alighting stops, and a note about nearby walkable stops — without forcing the passenger to pick between identical names when simply crossing the road suffices.

**Why this priority**: This is the reported defect. Refusing on an exact stop id when the passenger named the wrong side of the road forces a needless pick, even though the answer (cross the road) is obvious once nearby stops are considered.

**Independent Test**: Ask an area-to-area question whose destination has opposite-side duplicates plus a walkable mate, and confirm the answer names the exact stops, the route with its evidence link, and the walk note — with no pick prompt shown.

**Acceptance Scenarios**:

1. **Given** a destination group with opposite-side stops (K1/K2) plus a walkable mate (K3), **When** a direct route serves one of them from the passenger's origin, **Then** the answer names that exact alighting stop and notes the walkable mates with their walk distances, without asking the passenger to pick.
2. **Given** an area-to-area question, **When** the helper answers, **Then** every cited route carries its `/routes/:id` evidence and a walk-distance note naming the exact alighting stop.
3. **Given** a direct route exists for some member pair, **When** the passenger reads the answer, **Then** no exact-id refusal is returned for the merely wrong-side case.

---

### User Story 2 - Origin ambiguity handled the same way (Priority: P1)

A passenger's origin is the ambiguous end (for example several same-named boarding stops across two clusters). The helper applies the identical group-first flow symmetrically: resolve origin groups, test all member pairs, and answer per route with exact stops plus walk notes — rather than asking which origin stop the passenger means when a nearby one serves.

**Why this priority**: Origin and destination ambiguity are the same problem mirrored; fixing only the destination end leaves half the needless picks in place.

**Independent Test**: Ask a question whose origin has same-named duplicates and confirm the answer resolves them with the same group-first, matrix-test, walk-note flow as a destination-ambiguous question, with no pick prompt when a walkable boarding stop serves.

**Acceptance Scenarios**:

1. **Given** an ambiguous origin with same-named stops, **When** a direct route serves a walkable origin member, **Then** the answer names that exact boarding stop with its walk note and no pick prompt.
2. **Given** both ends are ambiguous, **When** the helper answers, **Then** both ends went through the group-first flow and the answer is exact on both ends.

---

### User Story 3 - Pick prompt only after tools find nothing viable (Priority: P2)

When no member pair across the resolved groups yields a direct route, the helper falls back honestly: it refuses politely when every tested pair fails, or offers the map/list pick (per the choose-on-map flow) when pairs went untested or the place never matched — but only at that point, never before the tool checks are exhausted.

**Why this priority**: The pick prompt is the fallback, not the first step. Asking first is the current defect; asking last keeps the fast path fast while preserving an honest path for genuinely unserved pairs.

**Independent Test**: Ask a question with no direct route between any tested pair and confirm the helper refuses politely; ask one where pairs went untested or the place never matched and confirm it offers the map/list pick; ask one with a direct route and confirm no pick prompt appears.

**Acceptance Scenarios**:

1. **Given** all tested pairs yield no viable route and the place matched, **When** the helper responds, **Then** it refuses politely with a no-direct-service reason — and the tool checks ran first.
2. **Given** pairs went untested (pair-cap truncation) or the place never matched, **When** the helper responds, **Then** it offers the map/list pick instead of refusing.
3. **Given** at least one viable pair exists, **When** the helper responds, **Then** no map/list pick prompt is shown.

---

### Edge Cases

- Opposite direction only: a route serving the pair only in reverse (boarding position after alighting position) is not viable and drops out; it MUST NOT be cited as a direct service.
- Same stop on both ends (from == to): the pair is skipped, never cited.
- Unknown place name: group resolution returns nothing (the place never matched), so the helper offers the map/list pick for re-resolution rather than refusing.
- Far groups with no direct route (for example kaloor#2's K4/K5): onward walk-to-corridor routing is out of scope; the helper answers what is directly reachable and falls back honestly for the rest without inventing an onward leg.
- Single-stop names: the flow degenerates to a single-pair check and MUST still work — group-first with one member is not an error.
- Walk boundary: a mate at exactly 150m counts as walkable (d <= 150m is inclusive).
- Group route counts are display hints only: a group listing a route MUST NOT be cited as proof that any particular member is served; proof comes only from the pair test plus route detail.
- No bypass: old answer_direct single-pair path is replaced as entry flow and kept only as leaf verifier if needed. Picks never shortcut verification.
- Over-wide map area: a `zoom_in` result MUST lead to a narrow-the-area request or the map prompt, never to a silent substitution or an invented answer.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The helper MUST resolve both the origin and the destination to place groups via `search_places` before asking the passenger to pick a stop. When the request carries an explicit map area for an end (for example map context from the choose-on-map flow), that end MUST be resolved via `search_places` bbox; name text MUST be resolved via query. When both are present for the same end, the explicit map area wins. A live shared location MUST NOT replace a named end in this feature (shared-location origin is deferred).
- **FR-002**: The helper MUST test origin-member by destination-member pairs via `find_routes_matrix`, keeping only pairs served by a route where boarding position is before alighting position (`pos_from < pos_to`). Group pairs MUST be tested nearest-first, where nearness is the minimum member-to-member stop distance across the two ends (the closest actual boarding-alighting pair); truncation under the cap MUST drop the farthest pairs first. The cap value is a planning-time decision recorded in the plan.
- **FR-003**: For each viable route, the helper MUST classify the direct exact stop plus nearby mates in the same group with d <= 150m, where d comes from new read-only distance_m lat1 lon1 lat2 lon2 using haversine, inclusive at 150m.
- **FR-004**: Every cited route MUST be answered with its `/routes/:id` evidence plus a walk-distance note naming the exact alighting (and boarding) stop and the nearby mates with their walk distances, ordered nearest-first with `walk_m` in whole meters. At most 5 destinations MUST be cited, ranked by operator group, then stop count, then route id. The maximum mates noted per route and the exact answer prose template are planning-time decisions recorded in the plan.
- **FR-005**: The helper MUST NOT initiate a map/list pick prompt before the tool checks find nothing viable across the tested pairs — never before or instead of the checks. A passenger's explicit pick (map tap, list choice, or typed exact stops) MUST be accepted as member selection and verified through the same matrix flow; it MUST NOT count as the helper having asked.
- **FR-006**: Origin ambiguity MUST follow the same group-first, matrix-test, walk-note flow as destination ambiguity (symmetric handling).
- **FR-007**: When every tested pair yields no viable route and the place matched, the helper MUST refuse politely (no direct service) and MUST NOT invent stops, routes, or journeys. The map/list pick MUST be offered instead only when pairs went untested (pair-cap truncation) or the place never matched.
- **FR-008**: Group-level route counts MUST NOT be treated as proof that an exact member is served; proof MUST come from the matrix pair test re-checked against route detail.
- **FR-009**: A read-only `nearby_stops(lat, lon, radius_m)` tool MUST be created now so the next feature can use it: default radius 500m, an enforced maximum radius set at planning time, at most 100 stops returned ordered by ascending `distance_m`, and an error (never an invented list) for invalid coordinates or an over-maximum radius. Shared-location origin handling itself is out of scope for this feature.
- **FR-010**: A wrong-side exact stop MUST NOT produce an exact-id refusal when a walkable mate of the same group is directly served; the helper MUST answer with the served stop plus the walk note instead.
- **FR-011**: Agent search MUST go only through the agent loop search_places to find_routes_matrix to get_route_detail. No single-pair find_routes shortcut may answer inside run_journey, even for exact map taps or familiar users. A tap selects a member id only. If no viable pair exists, the helper may suggest direct from-to search for familiar users, but MUST NOT run it as the answer.
- **FR-012**: When `search_places` returns `empty` for a name query (the place never matched), the helper MUST offer the map/list pick so the passenger can re-resolve. When it returns `zoom_in` for a map-area query, the helper MUST ask the passenger to narrow the area (or offer the map prompt); it MUST NOT silently substitute a different area.

### Key Entities

- **Place group**: Stops sharing one place name within one recognizable cluster (for example kaloor#1 = {K1, K2, K3}, kaloor#2 = {K4, K5}). Has the shared name, members, and route hints. Group shape (center, bbox, spread_m, route_count) is governed by `specs/009-place-groups/contracts/places.md` and unchanged by this feature.
- **Walk distance**: Haversine meters from `distance_m`, same formula as grouping with R = 6371000.0. Reported as `walk_m` per mate.
- **Member stop**: One existing stop inside a group. Opposite-side duplicates are ordinary members.
- **Viable pair**: An origin member plus a destination member served by one route with `pos_from < pos_to`. The only basis for citing a direct service.
- **Direct exact stop**: The member of the pair the route actually serves; named exactly in the answer.
- **Walkable mate**: A same-group member within d <= 150m of the direct exact stop; reported with its walk distance, never cited as served itself.
- **Evidence citation**: The `/routes/:id` link grounding each cited route in canonical data.
- **Nearby-stops result**: Distance-ordered stops around a point from `nearby_stops`; created now, consumed by the next feature.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In trials of area-to-area questions where a direct route serves a group member (including wrong-side cases like K1 vs K2), 9 out of 10 answers name the exact stops with evidence and walk note and show no pick prompt.
- **SC-002**: Zero exact-id refusals occur in trials where a walkable mate of the named stop is directly served (crossing the road suffices).
- **SC-003**: Every map/list pick prompt observed in trials is preceded by an exhausted tool check (pair test across the tested pairs in nearest-first member-distance order up to the documented cap, with nothing viable); no prompt appears when a tested viable pair exists.
- **SC-004**: A trial audit of cited routes finds every citation resolves to its `/routes/:id` evidence with correct boarding-before-alighting order, and no invented stops, routes, or onward legs.
- **SC-005**: Origin-ambiguous trial questions resolve with the same exact-stop-plus-walk-note shape as destination-ambiguous ones, with no asymmetric pick prompts.

## Assumptions

- Place groups come from the existing grouping behavior (shared name plus proximity clustering, per the place-groups feature); kaloor#1 = {K1, K2, K3} and kaloor#2 = {K4, K5} is the illustrative example, not live data.
- The 150m grouping-cluster radius and the 150m walkable-mate threshold are two independent constants that happen to share a value; planning may confirm or adjust either one without the other, documented in the plan rather than this spec.
- Single-ended questions (for example "Kaloor buses?" with no origin) are out of scope and keep their existing behavior; this feature covers two-ended area-to-area questions only.
- Far-group onward routing (walk from a far group to an onward corridor, for example reaching K4/K5) is out of scope; the matrix test still covers far-group members for direct routes, but no walk-plus-onward leg is constructed.
- Shared-location origin (deriving the origin from a shared point instead of a name query) is out of scope; `nearby_stops` is created now purely to unblock the next feature.
- The product stays direct-services-only with no schedules, times, durations, frequencies, or transfers, and every AI answer stays evidence-grounded, refuses when unknown, and links `/routes/:id` (constitution principles VIII and IX).
- Tools are read-only over the application's own dataset; group route counts remain display hints and never proof (constitution principles V, VI, and IX).
- MVP validation framing holds: this feature directly serves "How do I get from A to B?" for direct services without accounts or tracking (constitution principles I and III).
