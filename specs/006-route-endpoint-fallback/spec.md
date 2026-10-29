# Feature Specification: Route Endpoint Fallback

**Feature Branch**: `006-route-endpoint-fallback`

**Created**: 2026-10-29

**Status**: Draft

**Input**: User description: "When OSM from/to tags are absent, the read API should fall back to endpoint stop names for route origin/destination in list, detail, and connectivity responses, so cards, details, and evidence never disagree."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Route detail names its endpoints (Priority: P1)

A passenger opens a route whose OSM tags carry no `from`/`to`
text. The detail still shows an origin and a destination —
the names of its first and last stops in travelling order —
instead of blank fields, matching what the route card shows.

**Why this priority**: This is the exact disagreement the
passenger reported: card shows endpoint info, detail shows
blanks. Fixing the detail closes the reported gap.

**Independent Test**: Open the detail of a servable route
with null stored origin/destination but recorded stops, and
confirm origin equals the first ordered stop's name and
destination equals the last ordered stop's name.

**Acceptance Scenarios**:

1. **Given** a servable route with blank stored origin and
   recorded stops, **When** its detail is opened, **Then**
   the origin is the name of the stop with `is_origin`
   true.
2. **Given** a servable route with blank stored destination
   and recorded stops, **When** its detail is opened,
   **Then** the destination is the name of the stop with
   `is_terminus` true.
3. **Given** a route with non-blank stored origin or
   destination text, **When** its detail is opened,
   **Then** the stored text is served unchanged — the
   fallback never overwrites it.
4. **Given** a servable route with no recorded stops,
   **When** its detail is opened, **Then** origin and
   destination stay blank — nothing is invented.

---

### User Story 2 - Cards, details, and evidence agree (Priority: P2)

A passenger comparing a route card, its detail overlay, and
any cited evidence sees the same origin and destination in
all three places, because the list and connectivity results
apply the identical fallback.

**Why this priority**: Fixing only the detail would move the
disagreement instead of removing it. Consistency across all
three shapes is the actual done condition.

**Independent Test**: For a set of tag-less routes with
stops, compare list, detail, and connectivity responses and
confirm identical origin/destination in all three.

**Acceptance Scenarios**:

1. **Given** a tag-less route with stops, **When** the
   routes list is read, **Then** its origin/destination
   equal the endpoint stop names from its detail.
2. **Given** a tag-less route serving a connectivity query,
   **When** the result is read, **Then** its
   origin/destination equal the endpoint stop names.
3. **Given** any route, **When** list, detail, and
   connectivity are compared, **Then** the three shapes
   carry the same origin/destination values.

---

### Edge Cases

- What happens when a tag-less route has exactly one stop?
  Origin and destination are both that stop's name (it is
  origin and terminus at once).
- What happens when stored text is blank/whitespace rather
  than null? Treated as absent — the fallback applies.
- What happens to routes with stored text, unknown ids, or
  withheld routes? Unchanged: stored text wins, unknown and
  withheld ids keep their existing plain-language 404s.
- What happens to search, paging, throttling, and errors?
  Nothing — this feature changes field values only, never
  query behavior, envelopes, or status codes.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: When a route's stored origin is null or blank,
  route detail MUST serve the name of its first ordered stop
  (`is_origin`) as origin.
- **FR-002**: When a route's stored destination is null or
  blank, route detail MUST serve the name of its last ordered
  stop (`is_terminus`) as destination.
- **FR-003**: The routes list MUST apply the identical
  fallback to its origin/destination fields.
- **FR-004**: Connectivity results MUST apply the identical
  fallback to their origin/destination fields.
- **FR-005**: Non-blank stored text MUST take precedence;
  the fallback MUST never overwrite or alter stored values.
- **FR-006**: Routes with no recorded stops MUST keep null
  origin/destination — the fallback MUST NOT invent names.
- **FR-007**: Response shapes, envelopes, hidden-field rules,
  and error behavior MUST stay exactly as contracted in
  `specs/003-read-map-api` — values change, the contract
  does not.

### Key Entities *(include if feature involves data)*

- **Route endpoint (derived, not stored)**: The first
  (`is_origin`) and last (`is_terminus`) ordered membership
  stops of a route, used only as a display fallback when
  stored text is absent. Nothing is written back to the
  dataset.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of servable routes with stops serve
  non-null origin and destination in list and detail, and
  card/detail/evidence values agree in 100% of sampled
  comparisons.
- **SC-002**: 100% of routes with stored text serve byte-
  identical origin/destination before and after the change.
- **SC-003**: The full pre-existing backend suite stays
  green with zero test modifications for behavior (new
  fallback tests added, none altered).

## Assumptions

- The `is_origin`/`is_terminus` marking established in 003
  is trusted as the endpoint definition.
- The fallback is computed at request time; no import
  rerun, migration, or stored-data change is required.
- A single-stop route shows the same stop name as both
  origin and destination.
- The 003 hidden-field and provenance rules apply unchanged:
  no tags, OSM ids, or masters leak through the fallback.
