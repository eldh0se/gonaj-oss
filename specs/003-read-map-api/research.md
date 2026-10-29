# Research: Read Map API

**Feature**: [spec.md](spec.md) | **Date**: 2026-10-29

The spec pinned the public behaviour (search fields, filter
semantics, envelope, bbox outcomes, connectivity rules), so no
NEEDS CLARIFICATION remained. Each decision below records what was
chosen, why, and what was set aside. All endpoint shapes are
normative in [contracts/read-map-api.md](contracts/read-map-api.md).

## Decision: Endpoints live in the transport app under `/api/v1/`

- **Decision**: Five GET reads — `GET /api/v1/routes/`,
  `GET /api/v1/routes/{id}/`, `GET /api/v1/stops/`,
  `GET /api/v1/stops/{id}/`, `GET /api/v1/connectivity/` —
  implemented in a new `backend/apps/transport/api/` subpackage and
  mounted next to the existing API root. GET only; all other verbs
  are refused.
- **Rationale**: The transport domain owns the tables being read;
  core keeps only version discovery. One versioned prefix preserves
  the 001 boundary for both the future frontend and AI tools.
- **Alternatives considered**: Views in `apps/core/` (rejected —
  core would grow domain knowledge); a separate `apps/api/` app
  (rejected — splits the domain from its read projection).

## Decision: Public identifier is the surrogate record id

- **Decision**: Detail URLs and cross-references use the record's
  database `id`. OSM identifiers (`osm_type`, `osm_id`) are never
  exposed: they are provenance (Principle V), and the spec requires
  provenance hidden (FR-007). Evidence links are therefore
  `/api/v1/routes/{id}/`, matching the `/routes/:id` evidence shape
  Principle IX requires the journey helper to cite.
- **Rationale**: Stable for the life of the row, meaningless to
  outsiders, and leak-free by construction.
- **Alternatives considered**: Expose `osm_id` as the public id
  (rejected — leaks source identity and couples clients to OSM
  renumbering); slug from name (rejected — names duplicate and
  collide, per 002's duplicate-name warnings).

## Decision: Servable dataset = non-quarantined, master-served routes; all stops

- **Decision**: The routes list and route detail serve only routes
  with `quarantined=False` that belong to a master through
  `RouteMasterMembership`. Quarantined (platform-less), orphan
  (master-less), and blocked-master routes answer with the same
  plain-language 404 as unknown ids. All imported stops are
  servable in the stops list and stop detail.
- **Rationale**: 002 defined quarantine/orphan/blocked as
  "recorded, not served". Serving them would publish data the
  import deliberately withheld; distinguishing them in errors
  would leak import internals.
- **Alternatives considered**: Serve quarantined routes with a flag
  (rejected — publishes withheld data and leaks the quarantine
  concept); serve orphans (rejected — 002 tracks them for review,
  not for passengers).

## Decision: Route search joins name, endpoints, and served stop names

- **Decision**: `?search=` is a case-insensitive containment match
  (`icontains`) over `Route.name`, `Route.from_text`,
  `Route.to_text`, and the `name`/`name_ml` of stops reached via
  `RouteStopMembership`, deduplicated at the query level only so a
  route matching through several stops appears once per stored
  route row. Blank/absent/whitespace `search` means no text
  filtering (browse-all). `?operator=` and `?network=` are exact
  (`iexact`-free, stored-value equality) filters resolved through
  `RouteMasterMembership → RouteMaster`, combined with `search`
  by AND. Masters themselves never appear in responses.
- **Rationale**: Matches the passenger mental model ("the bus
  through X", "from A to B") and the spec's exact-filter wording,
  while keeping the master as a filter-only join.
- **Alternatives considered**: Full-text search vectors (rejected —
  deferred complexity for ~930 routes; `icontains` is sufficient
  and predictable); exposing operator/network from the route row
  (rejected — those values live on the master; copying them would
  duplicate provenance-bearing data).

## Decision: List order preserves source order; duplicates preserved

- **Decision**: Routes order by master-membership position, then
  route id; stops order by name, then id; route-detail stops order
  by `RouteStopMembership.position`. No `distinct()` on route or
  stop identity: distinct stored rows (including duplicate names
  and duplicate platform stops within a route) each appear.
  Query-level deduplication for the stop-name join (above) removes
  only join fan-out, never stored rows.
- **Rationale**: The spec requires stored order and duplicates
  preserved (FR-006); 002 stored that order in membership
  `position`/`source_index`, so the read side honours it instead
  of inventing an alphabetical truth.
- **Alternatives considered**: Alphabetical reordering (rejected —
  silently rewrites source order); `distinct()` everywhere
  (rejected — would silently dedupe, which 002 forbids).

## Decision: Custom pagination producing the shared envelope

- **Decision**: A single pagination class for all three lists
  emitting exactly `count`, `results`, `total_pages`,
  `current_page`, `page_size`, with `?page=` (default 1) and
  `?page_size=` (default 20, capped at 100; larger requests are
  served at 100). A page beyond the end returns an empty `results`
  page with correct totals. Non-numeric or non-positive values
  produce the plain-language error, never a 500.
- **Rationale**: The envelope is user-mandated (FR-019) and shared
  by routes, stops, and connectivity; one class keeps the three
  lists byte-compatible in shape.
- **Alternatives considered**: DRF's default `PageNumberPagination`
  (rejected — emits `next`/`previous` links and no
  `total_pages`/`current_page`/`page_size` fields); cursor
  pagination (rejected — map/browse clients need page totals).

## Decision: Bounding box as one `bbox` parameter with closed bounds

- **Decision**: `GET /api/v1/stops/?bbox=min_lon,min_lat,max_lon,max_lat`
  filters with `lon__gte/lte` and `lat__gte/lte` (closed bounds,
  FR-009) over the existing float columns and B-tree index — no
  GeoDjango. Supplying both `bbox` and `search` (non-blank) is a
  plain-language 400 (FR-008). Malformed, inverted, or
  out-of-range coordinates are the same plain-language 400.
- **Rationale**: One parameter keeps the "either/or" rule trivially
  checkable and matches map-client conventions (Leaflet bounds
  serialise directly to this form).
- **Alternatives considered**: Four separate `min_lat`… parameters
  (rejected — partial-parameter states multiply error cases);
  PostGIS `Polygon`/`contains` (rejected — native GIS dependency
  chain for a rectangle range query the B-tree already serves).

## Decision: Oversized area threshold is a span constant; outcomes are 200s

- **Decision**: If either bbox span exceeds
  `MAX_BBOX_SPAN_DEGREES = 0.5` degrees (≈55 km — larger than the
  GCDA extent, small enough to keep a map page renderable), the
  stops list returns HTTP 200 with the shared envelope
  (`count: 0`, `results: []`) plus `status: "zoom_in"` and a
  plain-language `detail` telling the caller to zoom in — never a
  partial list (FR-010). A valid bbox with no stops returns 200
  with `status: "empty"` and the empty envelope (FR-011). Normal
  bbox and text searches return `status: "ok"`. The `status`/
  `detail` fields are additive: envelope fields are always present
  with the same names.
- **Rationale**: Oversized and empty are normal map outcomes, not
  caller faults, so they must not look like errors to passengers
  or AI tools; the span constant is the plan-time value the spec's
  Assumptions delegate here, applied uniformly.
- **Alternatives considered**: HTTP 400 for oversized (rejected —
  punishes ordinary map panning); silently clamping the bbox
  (rejected — returns a partial list under a false extent, exactly
  what FR-010 forbids); area (degrees²) threshold (rejected — span
  is predictable for wide-but-short viewports and simpler to test).

## Decision: Connectivity is a same-route ordered-membership lookup

- **Decision**: `GET /api/v1/connectivity/?from={stop_id}&to={stop_id}`
  joins `RouteStopMembership` twice (origin membership, destination
  membership) on the same servable route with
  `origin.position < destination.position`, returning each matching
  route once with an `evidence` link to its route detail. Missing,
  non-numeric, identical, or unknown stop ids produce the
  plain-language error; no matching route returns the empty
  envelope. No times, durations, or transfers are ever computed
  (FR-016–FR-018).
- **Rationale**: Order-aware containment is exactly "direct service
  from A to B" and nothing more — no routing engine (Principle VI)
  and no invented times (Principles VIII/IX). The empty list is the
  honest refusal the AI helper needs.
- **Alternatives considered**: Pathfinding over a stop graph
  (rejected — that is the deferred journey planner); ignoring
  position order (rejected — would claim reverse-direction routes
  as direct connections).

## Decision: Serializers whitelist public fields; errors share one plain-language shape

- **Decision**: Serializers expose only whitelisted fields (routes:
  `id`, `name`, `origin`, `destination`, `operator`, `network`;
  stops: `id`, `name`, `name_ml`, `lat`, `lon`, plus serving routes
  in detail; route detail adds ordered `stops[]` with `position`
  and origin/terminus markers — full shapes in the contract).
  `tags`, `import_run`, `osm_*`, verdicts, quarantine flags, and
  master objects are structurally absent, not nulled. A custom DRF
  exception handler renders every error as
  `{"detail": "<plain sentence>"}` with 400/404 as appropriate —
  no field names, SQL, or source references.
- **Rationale**: Whitelisting makes FR-007 true by construction
  (new internal fields cannot leak by accident) and gives
  passengers and AI tools one predictable error shape (FR-015,
  FR-020).
- **Alternatives considered**: Blacklist exclusion of known-private
  fields (rejected — the next internal field leaks by default);
  DRF default error payloads (rejected — field-keyed, technical).

## Decision: Open access with basic per-IP throttling; no tracking

- **Decision**: `AllowAny` on all five reads with no authentication
  classes engaged for this API, no cookies, no analytics, and no
  logging of query text beyond Django's ordinary server logs. No
  `REST_FRAMEWORK` global auth defaults are introduced. Basic abuse
  protection is DRF throttling shared across all five reads:
  180 requests/minute and 5,000/day per client IP, then the
  plain-language 429 with a `Retry-After` header. Counters live in
  Django's database cache on the existing PostgreSQL
  (`DatabaseCache` via `createcachetable`), keyed by a SHA-256
  hash of the client IP with expiry equal to the window — raw IPs
  are never stored or used as keys. The throttle identity is the
  direct connection address (`REMOTE_ADDR`); a forwarded-for
  header is trusted only when the deployment configures a known
  proxy (an explicit trusted-proxy setting, default off), so
  unconfigured callers cannot spoof fresh identities. Rates are
  settings, so tests can lower them and deployments can tune
  without code changes. No captcha, accounts, or API keys.
- **Rationale**: Principle III and FR-002/FR-003 are requirements,
  not defaults to inherit accidentally; stating them makes a later
  global-settings change visibly break this feature's tests. The
  hashed, expiring counter is transient abuse control, not
  identification: it answers "how many requests lately from this
  address" and forgets the answer with the window, which is the
  minimum that stops request loops and bulk scraping for a small
  MVP audience (clarifications, 2026-10-29).
- **Alternatives considered**: No throttling (rejected by the
  product owner — basic protection is required from launch);
  captcha or API keys (rejected — friction and identity for a
  no-accounts product, explicitly out of scope); Redis counters
  (rejected — Principle VI defers new services; the existing
  database is ample at MVP traffic); in-memory per-process
  counters (rejected — the limit would multiply per worker and
  reset on restart); raw-IP keys or abuse logs (rejected —
  retention turns abuse control into tracking under Principle III).

