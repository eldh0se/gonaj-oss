# Contract: Read Map API

**Feature**: [spec.md](../spec.md) | **Date**: 2026-10-29

All five reads of the public transport API. Every endpoint is
`GET`-only, requires no authentication, and sets no tracking
identifiers (spec FR-001–FR-003). Consumers: the passenger frontend
and AI tools — the same shapes for both. Behaviours referenced as
FR/SC are from [spec.md](../spec.md); decisions are from
[research.md](../research.md).

## Shared rules

### List envelope (FR-019)

Every list response (`routes`, `stops`, `connectivity`) is HTTP
`200` with exactly this envelope, plus only the additive fields
noted per endpoint:

```json
{
  "count": 42,
  "results": [],
  "total_pages": 3,
  "current_page": 1,
  "page_size": 20
}
```

- `count`: total items matching the query (all pages).
- `results`: the current page of items (shapes below).
- `total_pages`: `ceil(count / page_size)`; `0` when `count` is `0`.
- `current_page`: the served page (`?page=`, default `1`). A page
  beyond the end serves `results: []` with correct totals.
- `page_size`: the served page size (`?page_size=`, default `20`,
  maximum `100`; requests above `100` are served at `100`).
- Non-numeric or non-positive `page`/`page_size` values are the
  plain-language `400` below — never a `500`.

### Errors (FR-015, FR-020)

Every error is a single plain-language sentence a passenger can act
on. No field names, database messages, OSM identifiers, or stack
details ever appear.

```json
{ "detail": "We could not find that route. Please check the link and try again." }
```

| Case | Status | `detail` (shape; wording may be polished, meaning may not change) |
|------|--------|-------------------------------------------------------------------|
| Unknown or withheld route id | `404` | Could not find that route |
| Unknown or withheld stop id | `404` | Could not find that stop |
| Stops: `search` and `bbox` together | `400` | Search by name or by map area, not both at once |
| Stops: malformed/inverted/out-of-range `bbox` | `400` | That map area does not look right — four coordinates in range, near corner first |
| Invalid `page`/`page_size` | `400` | That page request does not look right |
| Connectivity: missing/non-numeric/equal/unknown stop ids | `400` | Please choose two different stops to check |
| Any non-GET verb on these paths | `405` | This service is read-only (DRF default body replaced by this shape) |
| Over the per-IP rate limit | `429` | Too many requests — please wait a moment and try again, with a `Retry-After` header giving the wait in seconds |

### Rate limiting (FR-021–FR-024)

All five reads share one per-IP budget: 180 requests/minute and
5,000 requests/day, counted across every endpoint combined.
Identity is the direct connection address; a forwarded-for header
counts only when the deployment configures its known proxy.
Over-limit requests receive the `429` above — never data. Counters
are hashed-IP keys expiring with their window in the existing
database cache; raw IPs are never stored. No captcha, account, or
API key exists at any limit.

Withheld ids (quarantined, orphan, blocked-master routes) return
the identical `404` as unknown ids (research Decision 3).

### Hidden in every response (FR-007)

No response ever contains: `tags`, `osm_type`, `osm_id`,
`import_run`, snapshot/recipe/provenance fields, `verdict`,
`quarantined`, `direction`, `source_index`, or any master object.
`operator`/`network` values are exposed (they are passenger-facing
facts) without the master they came from.

## `GET /api/v1/routes/` — browse and search routes (FR-004–FR-006)

**Query parameters** (all optional, combined by AND):

| Param | Meaning |
|-------|---------|
| `search` | Case-insensitive containment over route name, origin, destination, and served stop names. Absent/empty/whitespace = browse-all. |
| `operator` | Exact match on the route's operator. |
| `network` | Exact match on the route's network. |
| `page`, `page_size` | Shared envelope rules. |

**Success — `200`** with the shared envelope. Each result:

```json
{
  "id": 17,
  "name": "Ernakulam — Fort Kochi",
  "origin": "Ernakulam",
  "destination": "Fort Kochi",
  "operator": "KSRTC",
  "network": null
}
```

- `origin` is the stored origin text, `destination` the stored
  destination text; `name`, `operator`, `network` are `null` when
  not held — never invented.
- Order: master-membership position, then `id`. Stored duplicates
  are preserved; a route matching the search through several stops
  still appears once per stored route row.
- Only servable routes appear (research Decision 3). No matches =
  `count: 0, results: []` with `200` — an empty list, not an error.

## `GET /api/v1/routes/{id}/` — route detail (FR-013, FR-014)

**Success — `200`**:

```json
{
  "id": 17,
  "name": "Ernakulam — Fort Kochi",
  "origin": "Ernakulam",
  "destination": "Fort Kochi",
  "operator": "KSRTC",
  "network": null,
  "stops": [
    {
      "stop": { "id": 101, "name": "Ernakulam South", "name_ml": null, "lat": 9.968, "lon": 76.29 },
      "position": 1,
      "is_origin": true,
      "is_terminus": false
    }
  ]
}
```

- `stops` is ordered by `position`; the first step has
  `is_origin: true`, the last `is_terminus: true` (a single-stop
  route has both `true`). Duplicate platform steps appear as
  separate entries in stored order.
- A servable route with no memberships returns `200` with
  `"stops": []` — explicit, never an error (FR-014; such a route is
  reachable only if it is servable yet membership-empty — withheld
  platform-less routes still `404`).
- Unknown or withheld `id` = the plain-language `404` above.

## `GET /api/v1/stops/` — find stops by name or map area (FR-008–FR-011)

Exactly one mode per request. Supplying both is the `400` above;
supplying neither is a name browse-all (empty search = all stops,
paginated).

| Param | Mode | Meaning |
|-------|------|---------|
| `search` | text | Case-insensitive containment over stop `name`/`name_ml`. |
| `bbox` | area | `min_lon,min_lat,max_lon,max_lat` (four comma-separated numbers). Closed bounds: edge/corner stops are included. |
| `page`, `page_size` | both | Shared envelope rules. |

**Success — `200`** with the shared envelope plus `status` (and
`detail` when `status` is not `"ok"`). Each result:

```json
{ "id": 101, "name": "Ernakulam South", "name_ml": null, "lat": 9.968, "lon": 76.29 }
```

| Situation | `status` | Envelope |
|-----------|----------|----------|
| Normal text or bbox results (possibly paginated) | `"ok"` | Matching stops |
| Valid bbox, no stops inside | `"empty"` | `count: 0, results: []` — a normal outcome, not an error (FR-011) |
| Bbox span over `0.5°` on either axis | `"zoom_in"` | `count: 0, results: []`, `detail` asks the caller to zoom in — never a partial list (FR-010) |

Example oversized response:

```json
{
  "count": 0,
  "results": [],
  "total_pages": 0,
  "current_page": 1,
  "page_size": 20,
  "status": "zoom_in",
  "detail": "That area is too large to list stops for. Please zoom in on the map and try again."
}
```

## `GET /api/v1/stops/{id}/` — stop detail (FR-012)

**Success — `200`**; coordinates and serving routes are always
present:

```json
{
  "id": 101,
  "name": "Ernakulam South",
  "name_ml": null,
  "lat": 9.968,
  "lon": 76.29,
  "serving_routes": [ { "id": 17, "name": "Ernakulam — Fort Kochi" } ]
}
```

- `serving_routes` lists servable routes only, in routes-list
  order; when none serve the stop it is `[]` — explicit, never
  omitted (FR-012).
- Unknown `id` = the plain-language `404` above.

## `GET /api/v1/connectivity/` — direct routes between two stops (FR-016–FR-018)

**Query parameters** (both required):

| Param | Meaning |
|-------|---------|
| `from` | Public `id` of the boarding stop. |
| `to` | Public `id` of the alighting stop (must differ from `from`). |
| `page`, `page_size` | Shared envelope rules. |

**Success — `200`** with the shared envelope. Each result is one
route serving `from` before `to` in travelling order:

```json
{
  "id": 17,
  "name": "Ernakulam — Fort Kochi",
  "origin": "Ernakulam",
  "destination": "Fort Kochi",
  "operator": "KSRTC",
  "network": null,
  "from_position": 1,
  "to_position": 9,
  "evidence": "/api/v1/routes/17/"
}
```

- Direction matters: routes serving both stops only in reverse
  order are absent. Each matching route appears once.
- `evidence` is the route-detail URL an AI tool cites for the
  claim (Principle IX); it always resolves to a `200` route detail.
- No route fields for times, durations, frequencies, or transfers
  exist anywhere in this response (FR-018).
- No matching route = `count: 0, results: []` with `200` — the
  honest "no direct service" answer, not an error.

## Non-goals (explicitly out of contract)

- No write verbs, no feedback submission, no AI endpoints, no
  schedule/timetable fields (Principles II, VIII, IX; later
  features own those).
- No master, provenance, import, or anomaly endpoints of any kind.
- No per-user keys, cookies, or tracking parameters; adding any
  requires a constitution-level decision (Principle III).
