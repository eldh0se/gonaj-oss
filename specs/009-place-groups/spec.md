# Feature Specification: Place Groups for Same-Named Stops

**Feature Branch**: `009-place-groups`

**Created**: 2026-10-31

**Status**: Draft

**Input**: User description: "Feature 009: group same-named stops into places. Passengers see 7 identical `Kaloor` buttons with no way to choose. Opposite-side duplicates are normal. What changes: search returns place groups with member count, centroid, spread meters, and route hints. Why: choosing among identical names is impossible without grouping."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Search shows place groups instead of identical buttons (Priority: P1)

A passenger unfamiliar with Kochi searches for a place such as "Kaloor". Instead of seven identical `Kaloor` buttons with no way to choose, the search returns one group per distinct place: each group shows the shared name, how many stops it contains, where it is (a representative point), how far apart its stops are spread in meters, and which routes serve it.

**Why this priority**: This is the reported defect. Without grouping, choosing among identical names is impossible and every downstream flow (map, journey helper) inherits the confusion.

**Independent Test**: Search a name known to have several same-named stops and confirm the results arrive as groups — each with member count, representative location, spread in meters, and route hints — rather than a flat list of identical names.

**Acceptance Scenarios**:

1. **Given** several stops share one name, **When** a passenger searches that name, **Then** the results arrive as one group per distinct place, each showing its member count.
2. **Given** a place group is shown, **When** the passenger reads it, **Then** it shows a representative location, the spread of its stops in meters, and the routes serving its members.
3. **Given** a name matches only one stop, **When** a passenger searches it, **Then** the result stays a single plain stop result with no group wrapper.

---

### User Story 2 - Choose the right place using route hints (Priority: P1)

A passenger who knows the bus they need (for example "the Fort Kochi bus") faces two same-named groups. Each group lists the routes serving its members, so the passenger picks the group whose routes match their need instead of guessing between identical names.

**Why this priority**: Unfamiliar users are the primary audience; route hints turn an unguessable choice into an informed one and feed the journey helper with a correctly resolved place.

**Independent Test**: Search a duplicated name, confirm every group lists its serving routes, pick the group matching a known route, and confirm the journey continues from that group's stops.

**Acceptance Scenarios**:

1. **Given** place groups are shown, **When** each group has serving routes, **Then** every group lists them (or states plainly that no known route serves it).
2. **Given** a passenger picks a place group, **When** the group is resolved, **Then** the journey helper continues from that group's stops without re-asking the already-answered place question.

---

### User Story 3 - Individual stops stay selectable inside a group (Priority: P2)

A passenger who knows exactly which side of the road they need (for example the east-side `Kaloor` boarding point) opens a place group and still sees each member stop individually — including opposite-side duplicates — and picks the exact stop.

**Why this priority**: Grouping must aid choice, never hide stops. Opposite-side duplicates are normal data; collapsing them into one unaddressable point would break boarding-side correctness.

**Independent Test**: Open a group containing opposite-side duplicates, confirm every member stop is listed individually with distinguishing detail, pick one member, and confirm the pick resolves to that exact stop.

**Acceptance Scenarios**:

1. **Given** a group contains opposite-side duplicate stops, **When** the passenger opens it, **Then** every member appears individually with distinguishing detail.
2. **Given** a passenger picks one member of a group, **When** the pick is resolved, **Then** it resolves to that exact stop, not to the group centroid.

---

### Edge Cases

- Same name, far apart: stops sharing a name but lying far beyond a recognizable walking cluster form separate groups; they MUST NOT merge into one misleading group with a huge spread.
- Member with no serving routes: the group still lists the member; its route hints state plainly that no known route serves it rather than omitting the member.
- Single-stop names: names matching exactly one stop return a plain stop result, never a one-member group wrapper.
- Unknown or empty search text: behaves exactly as search does today (no groups invented, honest empty result).
- Name variants: stops matching via alternate-language names group under the searched place the same way as primary-name matches.
- Data changes: grouping always reflects the current stop data; a re-import that moves or renames stops changes the groups accordingly with no stale groupings retained.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Search by place name MUST return place groups (one per distinct same-named place) instead of a flat list of identical stop names whenever several stops share the searched name.
- **FR-002**: Every place group MUST report its member count.
- **FR-003**: Every place group MUST report a representative location (centroid) for the group.
- **FR-004**: Every place group MUST report the spread of its member stops in meters.
- **FR-005**: Every place group MUST report route hints: the routes serving its member stops, or a plain statement that no known route serves it.
- **FR-006**: Stops sharing a name but lying beyond a recognizable walking cluster MUST form separate groups; a single group MUST NOT span far-apart places.
- **FR-007**: Every member stop MUST remain individually listed inside its group with distinguishing detail, and MUST remain individually selectable; opposite-side duplicates MUST be treated as ordinary members.
- **FR-008**: Wherever same-named candidates are offered for a journey choice, the choice MUST be offered as place groups first (group, then member), not as bare identical names.
- **FR-009**: A name matching exactly one stop MUST return a plain stop result with no group wrapper.
- **FR-010**: Grouping MUST be deterministic: the same search against unchanged data MUST return the same groups in the same order.

### Key Entities

- **Place group**: Stops sharing one place name that lie within one recognizable cluster. Has the shared name, member count, representative location, spread in meters, and route hints.
- **Member stop**: One existing stop inside a group. Has its identity, distinguishing detail (side, direction, nearby reference), and individually selectable behavior.
- **Route hint**: A route serving at least one member of a group. Listed per group so passengers match groups to the service they need.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Searching a name with 3 or more same-named stops returns groups — never 3 or more identical bare buttons — each showing member count, representative location, spread in meters, and route hints.
- **SC-002**: 9 out of 10 trial passengers facing identical names choose the intended place within two picks (group, then member where needed) with no repeated identical prompt observed.
- **SC-003**: Same-named stops planted far apart (beyond a walking cluster) always appear as separate groups in trials, never merged.
- **SC-004**: Every group member remains individually pickable in trials: picking a specific side-of-road member resolves to that exact stop.

## Assumptions

- Grouping is by shared name plus proximity; the exact walking-cluster distance is a planning-time decision documented in the plan, not in this spec.
- Opposite-side duplicates are normal data and ordinary group members, not errors.
- Route hints cover direct serving routes only, consistent with the direct-services-only product scope; no schedules, times, or transfers are involved.
- The product stays read-only with no accounts and no per-user memory; grouping is computed from the current canonical data on each request.
- Stop search ranking and map rendering are out of scope unless required to surface groups.
