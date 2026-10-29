# Feature Specification: Read Map API

**Feature Branch**: `003-read-map-api`

**Created**: 2026-10-29

**Status**: Draft

**Input**: User description: "03 read-map-api: public read-only transport API for passengers and AI tools. Routes collection supports search over name, origin, destination, stop name; blank means browse-all; supports exact operator and network filters; preserves order and duplicates; hides OSM tags, provenance, masters. One stops collection supports either text search or bounding-box filter exclusively; detail always includes coordinates and serving routes; closed bounds; oversized area returns zoom_in guidance with empty results, never partial; empty area returns empty status. Route detail returns ordered stops with origin and terminus positions; empty membership is explicit empty list; unknown ids return non-technical 404. Connectivity query returns direct routes containing both stops in order, evidence-linked, no times or transfers. All lists share envelope count, results, total_pages, current_page, page_size with default 20 cap 100. All errors plain-language. Open access, no auth, no tracking."

## Clarifications

### Session 2026-10-29

- Q: How strict should the per-IP rate limit be for these public read endpoints? → A: 180 requests/minute and 5,000/day per IP across all five reads, then plain-language 429 with retry guidance (Option A, recommended)
- Q: Where should the rate-limit counters live, and should client IPs be stored to enforce them? → A: Counters in the existing database cache with hashed IP keys that expire with the window; no raw IPs stored (Option B, recommended)
- Q: Which address should count as the client IP when the app sits behind a proxy or load balancer? → A: Use the direct connection address by default; trust the forwarded-for header only when a known proxy is configured (Option A, recommended)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Browse and search routes (Priority: P1)

A passenger (or an AI tool acting for a passenger) looks for a bus
service without knowing its exact name. They can browse every route,
or search by route name, origin, destination, or a stop the route
serves, and narrow the list by operator or network. Leaving the
search blank shows the full list so the passenger can discover what
exists.

**Why this priority**: Finding whether a service exists is the first
half of the MVP validation question ("How do I get from A to B?").
Without route discovery, neither the map nor the journey helper can
help anyone.

**Independent Test**: With the imported dataset in place, browse all
routes with a blank search, then search by a known route name,
origin, destination, and served stop name; each returns the expected
routes, and operator/network filtering narrows the list exactly.

**Acceptance Scenarios**:

1. **Given** the imported route dataset, **When** the passenger
   requests the routes list with a blank or absent search term,
   **Then** the full list of routes is returned (browse-all) in the
   shared list envelope.
2. **Given** the imported route dataset, **When** the passenger
   searches by route name, **Then** only routes whose name matches
   the term are returned.
3. **Given** the imported route dataset, **When** the passenger
   searches by origin or destination text, **Then** only routes whose
   origin or destination matches are returned.
4. **Given** the imported route dataset, **When** the passenger
   searches by a stop name, **Then** only routes that serve a stop
   with a matching name are returned.
5. **Given** a routes search, **When** the passenger adds an exact
   operator or network filter, **Then** only routes with exactly that
   operator or network value are returned, combined with the search
   term.
6. **Given** routes whose source data contains duplicate entries or
   a meaningful order, **When** the list is returned, **Then** the
   original order and duplicates are preserved exactly as stored —
   nothing is silently deduplicated or reordered.
7. **Given** any routes response, **When** the passenger or tool
   inspects it, **Then** no internal source details are exposed: no
   raw source tags, no provenance chain, and no grouping/master
   records appear in the public view.

---

### User Story 2 - Find stops by name or by map area (Priority: P1)

A passenger looks for a stop in two ways: by typing a stop name, or
by looking at the stops inside the map area they are viewing. Both
ways use the same stops list. A passenger can always see where a
stop is and which routes serve it.

**Why this priority**: Stops are the other half of route/stop
discovery (constitution Principle I as narrowed by Principle VIII).
The map cannot render and origin/destination picking cannot work
without a stops list that supports both name search and map-area
lookup.

**Independent Test**: Search stops by a known name fragment and
confirm the matching stops return; then request stops inside a small
map area and confirm exactly the stops inside that area return.

**Acceptance Scenarios**:

1. **Given** the imported stop dataset, **When** the passenger
   searches stops by a name fragment, **Then** matching stops are
   returned in the shared list envelope.
2. **Given** the imported stop dataset, **When** the passenger
   requests stops inside a map bounding box, **Then** stops whose
   location falls inside the box are returned. Stops exactly on the
   boundary are included (closed bounds).
3. **Given** the stops list, **When** the passenger supplies both a
   text search and a bounding box at once, **Then** the request is
   rejected with a plain-language explanation that only one filter
   may be used at a time — the two are never combined silently.
4. **Given** a bounding box covering an excessively large area,
   **When** the passenger requests stops in it, **Then** the
   response contains no stops and carries `zoom_in` guidance telling
   the passenger to zoom in — a partial list is never returned for an
   oversized area.
5. **Given** a bounding box covering an area with no stops, **When**
   the passenger requests stops in it, **Then** the response reports
   an explicit empty status with an empty result list, not an error.
6. **Given** any single stop, **When** the passenger opens its
   detail, **Then** the detail always includes its geographic
   coordinates and the list of routes that serve it.

---

### User Story 3 - Inspect a route and a stop in detail (Priority: P2)

A passenger who has found a candidate route opens it to see the
stops it serves in travelling order, where it starts, and where it
ends, so they can confirm it passes their boarding and alighting
points. A route with no recorded stops still opens cleanly.

**Why this priority**: Discovery alone does not let a passenger trust
a route. The ordered stop sequence with explicit origin and terminus
is what turns a search result into a usable journey leg, and it is
the evidence the connectivity answers link to.

**Independent Test**: Open a known route and confirm its stops
appear in travelling order with the first and last positions marked
as origin and terminus; open a stop and confirm its coordinates and
serving routes appear.

**Acceptance Scenarios**:

1. **Given** a route with recorded stops, **When** the passenger
   opens the route detail, **Then** the stops are returned in
   travelling order, each with its position, and the origin (first)
   and terminus (last) positions are explicitly identifiable.
2. **Given** a route with no recorded stop membership, **When** the
   passenger opens the route detail, **Then** the detail succeeds
   and the stop list is an explicit empty list — not an error and
   not a missing field.
3. **Given** a route or stop identifier that does not exist, **When**
   the passenger requests its detail, **Then** the response is a
   not-found result explained in plain, non-technical language.
4. **Given** any single stop, **When** the passenger opens its
   detail, **Then** the coordinates and serving routes are present
   even when the stop serves no routes (explicit empty serving list).

---

### User Story 4 - Check direct connectivity between two stops (Priority: P2)

A passenger — or the AI journey helper acting for them — asks
whether a direct service connects two stops: "Can I get from A to
B without changing?" The answer lists only routes that serve both
stops in the right order, and each answer links to the route
evidence so the passenger can verify it. No times and no transfers
are promised.

**Why this priority**: This is the read-side core of the narrowed
MVP validation question (route/stop discovery and service
availability, Principle VIII) and the exact evidence-grounded shape
the AI helper is allowed to give under Principle IX: connectivity
only, no schedules, no invented times, no transfers.

**Independent Test**: Pick two stops known to share a route in the
right order and confirm that route is returned with its evidence
link; reverse the order and confirm the route is no longer returned
as a direct connection.

**Acceptance Scenarios**:

1. **Given** two stops served by the same route in travelling order
   (origin stop before destination stop), **When** the passenger
   queries connectivity from the first to the second, **Then** that
   route is returned in the shared list envelope and each result
   links to the corresponding route detail as its evidence.
2. **Given** two stops served by the same route only in the reverse
   order, **When** the passenger queries connectivity in the forward
   direction, **Then** that route is not returned — direction and
   order matter.
3. **Given** two stops with no single route serving both in order,
   **When** the passenger queries connectivity, **Then** the result
   is an explicit empty list in the shared envelope — no transfer
   options, no times, and no invented services are suggested.
4. **Given** any connectivity response, **When** the passenger or
   tool inspects it, **Then** it contains no departure times, no
   durations, and no transfer instructions of any kind.

---

### Edge Cases

- What happens when the routes search term is blank (absent, empty,
  or whitespace only)? It means browse-all: the full route list is
  returned through normal pagination, never an error.
- What happens when a routes search matches nothing, or an exact
  operator/network filter matches nothing? An explicit empty list in
  the shared envelope, not an error.
- What happens when a stops request supplies both a text search and
  a bounding box? The request is rejected with a plain-language
  message stating the two filters are alternatives; no combined
  filtering is performed.
- What happens when a stops bounding box is oversized? The response
  carries `zoom_in` guidance with an empty result list and never a
  partial list, so clients never render a misleadingly incomplete
  map.
- What happens when a stops bounding box is valid but contains no
  stops? An explicit empty status with an empty result list, not an
  error.
- How are bounding-box boundaries treated? Bounds are closed: stops
  exactly on an edge or corner are included.
- What happens when a route has no recorded stops? Route detail
  succeeds with an explicit empty stop list when the route is
  otherwise servable; import-withheld platform-less routes return
  not-found instead (FR-014, FR-015).
- What happens when a route or stop identifier does not exist? A
  not-found response in plain, non-technical language; no internal
  identifiers, stack details, or source references are exposed.
- What happens when the same stop is given as both ends of a
  connectivity query, or a connectivity stop identifier does not
  exist? A plain-language explanation the passenger can act on; no
  routes are invented.
- What happens when pagination values are out of range (page beyond
  the end, page size above the cap, non-numeric values)? Page size
  is capped, out-of-range pages return an explicit empty page in
  the envelope, and invalid values produce a plain-language error —
  never a silent wrong result.
- What happens when duplicate stops or routes exist in the source
  data? They are preserved as stored in list responses; the public
  API never silently deduplicates or merges them.
- What happens when one client IP exceeds 180 requests/minute or
  5,000 requests/day across the five reads? Further requests are
  refused with the plain-language too-many-requests response and
  retry guidance until the window allows them again; other
  clients are unaffected (FR-021, FR-022).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The API MUST be read-only: it serves retrieval of
  routes, stops, route details, stop details, and connectivity, and
  MUST NOT create, modify, or delete any transit data.
- **FR-002**: The API MUST be openly accessible with no login, no
  user accounts, and no authentication required for any read
  operation (constitution Principle III).
- **FR-003**: The API MUST NOT track users, set tracking
  identifiers, or collect personal data; at most the minimal
  aggregate signals permitted by Principle III may be counted
  elsewhere, never per-user profiles from this API.
- **FR-004**: The routes list MUST support a text search that
  matches against route name, origin text, destination text, and
  the names of stops the route serves. A blank, absent, or
  whitespace-only search term MUST mean browse-all (the full route
  list).
- **FR-005**: The routes list MUST support exact-match filters for
  operator and for network. Filters combine with the text search;
  a filter value matches only routes whose stored value is exactly
  that value. Matching is exact stored-value equality and is
  case-sensitive: partial or differently-cased values match nothing.
- **FR-006**: Route list responses MUST preserve the stored order
  and any duplicates exactly as held in the dataset. The API MUST
  NOT deduplicate, merge, or reorder routes silently.
- **FR-007**: Public route and stop responses MUST NOT expose
  internal source details: no raw source tags, no provenance chain
  (source, import run, snapshot, recipe), and no grouping/master
  records. Provenance remains stored internally per Principle V
  but hidden from the public view.
- **FR-008**: There MUST be exactly one stops list. It MUST support
  two alternative modes — text search by stop name, or a geographic
  bounding-box filter — and MUST reject any request that supplies
  both at once with a plain-language error. The two modes are never
  combined. Supplying neither mode is a name browse-all (all stops,
  paginated), consistent with blank route search.
- **FR-009**: Bounding-box filtering MUST use closed bounds: stops
  whose coordinates lie exactly on the boundary are included.
- **FR-010**: When a bounding box exceeds the maximum servable area,
  the stops list MUST return an empty result list together with
  `zoom_in` guidance instructing the caller to zoom in. It MUST
  NEVER return a partial list for an oversized area.
- **FR-011**: When a valid bounding box contains no stops, the
  stops list MUST return an explicit empty status with an empty
  result list. An empty area is a normal outcome, not an error.
- **FR-012**: Stop detail MUST always include the stop's geographic
  coordinates and the list of routes serving that stop. When no
  route serves the stop, the serving list MUST be an explicit empty
  list.
- **FR-013**: Route detail MUST return the route's stops in
  travelling order, each with its sequence position, and MUST make
  the origin (first) and terminus (last) positions explicitly
  identifiable.
- **FR-014**: When a route has no recorded stop membership, route
  detail MUST succeed with an explicit empty stop list. An empty
  membership is a valid state, not an error and not a missing field.
  This applies to any servable route whose membership set is empty,
  however that state arises (for example, memberships later removed
  in curation). Routes withheld by import policy (such as
  quarantined platform-less routes) are not servable and return
  not-found under FR-015 instead.
- **FR-015**: Requests for a route or stop identifier that does not
  exist MUST return a not-found response explained in plain,
  non-technical language, with no internal or source details
  exposed.
- **FR-016**: The connectivity query MUST return only direct routes
  that contain both given stops in travelling order (the origin
  stop occurring before the destination stop on the same route).
  Routes serving both stops only in reverse order MUST NOT be
  returned.
- **FR-017**: Every connectivity result MUST link to its route
  detail as the verifiable evidence for the claim, so passengers
  and AI tools can cite the source route (Principle IX
  evidence-grounding).
- **FR-018**: Connectivity responses MUST NOT contain departure
  times, arrival times, durations, frequencies, or transfer
  instructions. Only direct, single-route connections are in scope
  (Principles VIII and IX).
- **FR-019**: Every list response (routes, stops, connectivity)
  MUST use the same envelope with exactly these fields: `count`
  (total matching items), `results` (the current page of items),
  `total_pages`, `current_page`, and `page_size`. The default page
  size MUST be 20 and the maximum page size MUST be capped at 100;
  requests above the cap are served at the cap.
- **FR-020**: Every error response across the API MUST be written in
  plain, non-technical language that tells a passenger or caller
  what went wrong and what they can do next. Errors MUST NOT expose
  internal implementation details, database messages, or source
  references.
- **FR-021**: Every read MUST be rate-limited per client IP across
  all five reads combined: at most 180 requests per minute and at
  most 5,000 requests per day. Requests beyond either limit MUST
  be refused with a plain-language too-many-requests response
  including retry guidance (see FR-022). Legitimate use below the
  limits MUST be unaffected. No captcha, account, or API key is
  required at any point.
- **FR-022**: The too-many-requests response MUST use the shared
  plain-language error shape (FR-020), tell the caller to wait and
  try again, and include machine-readable retry guidance so
  well-behaved clients can back off. It MUST NOT expose limit
  internals beyond what a caller needs to retry.
- **FR-023**: Rate-limit counters MUST be held in the project's
  existing database-backed cache, keyed by a hash of the client IP
  and expiring with their window (minute and day). Raw client IPs
  MUST NOT be stored, logged as throttle keys, or retained after
  the window expires, and no new cache or queue infrastructure is
  introduced for throttling (Principles III and VI).
- **FR-024**: The client IP for throttling MUST be the direct
  connection address by default. A forwarded-for header MUST be
  trusted only when the deployment explicitly configures a known
  proxy; unconfigured forwarded headers MUST be ignored so callers
  cannot mint fresh throttle identities by spoofing headers.

### Key Entities *(include if feature involves data)*

- **Route (public view)**: One direction/variant of a bus service as
  passengers see it. Attributes exposed: public identifier, name,
  origin text, destination text, operator, network. Internal source
  tags, provenance, and grouping/master relationships are held in
  the dataset but never exposed. A route serves an ordered sequence
  of stops (possibly empty).
- **Stop (public view)**: One boarding/alighting place. Attributes
  exposed: public identifier, name (including local-language name
  where held), geographic coordinates (latitude and longitude —
  always present in detail), and the routes that serve it.
  Coordinates are also the basis for bounding-box filtering.
- **Route Stop (ordered step)**: One stop's place in one route's
  travelling sequence. Carries the stop reference and its sequence
  position; the first step is the route's origin and the last step
  is its terminus. A route with no steps has an explicitly empty
  sequence.
- **Connectivity Result**: One direct connection claim: a route that
  serves both queried stops in order. Carries the route reference
  and a link to the route detail as evidence. It carries no times
  and implies no transfer.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A passenger can go from a blank routes browse to a
  specific route found by name, origin, destination, or served stop
  name in each case, with blank search returning 100% of routes
  (paginated) and each targeted search returning only matching
  routes.
- **SC-002**: 100% of route list responses preserve stored order and
  duplicates, and 0% of public responses (routes, stops, details,
  connectivity) expose raw source tags, provenance fields, or
  grouping/master records, verified by response inspection.
- **SC-003**: A passenger can find stops both by name fragment and
  by map area; 100% of stop detail responses include coordinates
  and a serving-routes list (explicitly empty when unserved).
- **SC-004**: For an oversized map area, 100% of stops responses
  return `zoom_in` guidance with zero stops and zero partial
  results; for a valid empty area, 100% return an explicit empty
  status rather than an error; for stops exactly on a bounding-box
  edge, 100% are included.
- **SC-005**: 100% of route detail responses return stops in
  travelling order with identifiable origin and terminus; routes
  with no stops return an explicit empty list in 100% of cases; and
  100% of requests for unknown route or stop identifiers return a
  plain-language not-found response.
- **SC-006**: In connectivity checks over a known test dataset,
  100% of returned routes serve both stops in the queried order,
  0% of reverse-order-only routes are returned, every result links
  to its route detail evidence, and 0% of responses contain times,
  durations, or transfer instructions.
- **SC-007**: 100% of list responses (routes, stops, connectivity)
  use the shared envelope (`count`, `results`, `total_pages`,
  `current_page`, `page_size`), serve 20 items per page by default,
  and never serve more than 100 items per page even when a larger
  page size is requested.
- **SC-008**: 100% of API reads succeed without login or accounts,
  and review confirms no user tracking or personal-data collection
  is introduced by this API.
- **SC-009**: A client exceeding 180 requests/minute or 5,000
  requests/day from one IP receives the plain-language
  too-many-requests response with retry guidance on 100% of
  over-limit requests, while clients below the limits complete
  100% of legitimate browse, search, detail, and connectivity
  flows unaffected and without any captcha, account, or key.

## Assumptions

- The dataset served is the application-owned dataset produced by
  the OSM snapshot import (`specs/002-osm-snapshot-import`): stops,
  routes, and their ordered memberships with GCDA scope. This
  feature adds no new source data and performs no import.
- Public identifiers for routes and stops are the stable
  identifiers of the imported records, exposed read-only; the API
  never invents or renumbers them.
- No schedule data is available in this phase, so — per
  constitution Principle VIII — this API exposes no timetables,
  trips, or times anywhere, including in connectivity answers.
  Schedule fields arrive only with a later phase that has real
  schedule data.
- The maximum servable bounding-box area (the threshold that
  triggers `zoom_in`) is a plan-time constant chosen so a single
  response stays renderable on the map; the exact value is fixed
  during planning and applied uniformly. The spec fixes the
  behaviour (guidance plus empty list, never partial), not the
  number.
- Text matching for route and stop search is a case-insensitive
  containment match over the named fields, consistent with a
  passenger typing a fragment; exact-match semantics apply only to
  the operator and network filters, as specified.
- Requests supplying both a stops text search and a bounding box
  are caller errors, not a combined-filter feature; the
  plain-language rejection in FR-008 is the intended behaviour.
- Aggregate, non-identifying usage counts (searches with and
  without results) remain governed by Principle III and are out of
  scope for this feature's responses; this API adds no per-user
  tracking to enable them.
- Initial traffic is very low (a small MVP audience). Throttle
  counters therefore live in the existing database cache with
  hashed, expiring keys; a dedicated cache service is deferred
  until traffic demonstrates the need (Principle VI).
- AI tools consume the same public read API and envelopes as the
  passenger frontend; no separate AI-only endpoint or privileged
  view is introduced (Principle IX: read-only tools, same evidence).

