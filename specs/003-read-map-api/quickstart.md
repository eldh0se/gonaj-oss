# Quickstart: Read Map API

**Feature**: [spec.md](spec.md) | **Date**: 2026-10-29

Validates the feature end to end against
[contracts/read-map-api.md](contracts/read-map-api.md). No
implementation code below — requests and expected outcomes only.
Examples assume the server from `docs/setup-backend.md` with the
sample import loaded; substitute real `id` values from the list
responses.

## Prerequisites

- Backend scaffold working per `docs/setup-backend.md` (database
  up, migrations applied).
- Dataset imported per `specs/002-osm-snapshot-import` (sample
  fixtures for the automated path; full GCDA snapshot for the
  manual path).
- No credentials: every request below is unauthenticated by design.

## 1. Browse and search routes (Story 1)

1. `GET /api/v1/routes/` — expect `200` with the shared envelope
   (`count`, `results`, `total_pages`, `current_page`,
   `page_size: 20`) listing routes in stored order.
2. `GET /api/v1/routes/?search=` (blank) — expect the identical
   browse-all result; then `?search=<known route name fragment>`,
   `?search=<origin text>`, `?search=<destination text>`, and
   `?search=<served stop name>` — expect only matching routes each
   time.
3. Add `&operator=<exact operator>` and `&network=<exact network>`
   — expect exact-match narrowing combined with the search. A
   partial operator value is expected to match nothing.
4. Inspect any response body — expect no `tags`, no `osm_*`, no
   provenance, and no master objects anywhere (FR-007).

## 2. Find stops by name or map area (Story 2)

1. `GET /api/v1/stops/?search=<stop name fragment>` — expect
   matching stops with `status: "ok"`.
2. `GET /api/v1/stops/?bbox=<small area around a known stop>` —
   expect exactly the stops inside, including any stop placed
   exactly on the boundary (closed bounds).
3. `GET /api/v1/stops/?search=x&bbox=...` (both) — expect the
   plain-language `400`: one filter at a time.
4. `GET /api/v1/stops/?bbox=<state-sized area>` — expect `200`
   with `status: "zoom_in"`, `count: 0`, `results: []`, and the
   zoom-in `detail`. Critically: zero stops, never a partial list.
5. `GET /api/v1/stops/?bbox=<ocean/empty area>` — expect `200`
   with `status: "empty"` and the empty envelope, not an error.

## 3. Route and stop detail (Story 3)

1. Take a route `id` from Step 1: `GET /api/v1/routes/{id}/` —
   expect ordered `stops[]` with `position`, first step
   `is_origin: true`, last step `is_terminus: true`.
2. Take a stop `id` from Step 2: `GET /api/v1/stops/{id}/` —
   expect `lat`/`lon` always present and `serving_routes` listing
   the routes from Step 1 that stop there (`[]` if none).
3. `GET /api/v1/routes/99999999/` and `GET /api/v1/stops/99999999/`
   — expect the plain-language `404` with no technical details.
   Repeat with a quarantined route's id — expect the identical
   `404` (withheld data does not leak).

## 4. Direct connectivity (Story 4)

1. From a route detail in Step 3, take its first and last stop ids:
   `GET /api/v1/connectivity/?from={first}&to={last}` — expect
   that route in the envelope with `from_position < to_position`
   and an `evidence` link; follow the link and expect the `200`
   route detail from Step 3.
2. Reverse them (`from={last}&to={first}`) — expect the route to
   disappear (empty envelope if nothing else serves that order).
3. Pick two stops no single route serves in order — expect
   `count: 0, results: []` with `200`. Inspect the body: no times,
   no durations, no transfer text anywhere.

## 5. Envelope and pagination (FR-019)

1. `GET /api/v1/routes/?page_size=5&page=2` — expect
   `page_size: 5`, `current_page: 2`, and `total_pages` consistent
   with `count`.
2. `GET /api/v1/routes/?page_size=500` — expect `page_size: 100`
   (capped) and at most 100 results.
3. `GET /api/v1/routes/?page=9999` — expect `200`, `results: []`,
   correct totals. `?page=abc` — expect the plain-language `400`.
4. Repeat Step 1 against `/api/v1/stops/` and
   `/api/v1/connectivity/` — expect the identical envelope field
   set on all three lists.

## 6. Read-only and open-access proof (FR-001–FR-003)

1. `POST /api/v1/routes/` (any body) — expect refusal (`405` in
   the shared plain-language shape) and no data change.
2. Repeat Steps 1–4 with no `Authorization` header and no cookies —
   expect identical results, and no `Set-Cookie` tracking headers
   introduced by this API.

## Automated suite

Run the transport API tests (`test_read_routes`, `test_read_stops`,
`test_connectivity`): green, covering search fields, exact filters,
order/duplicate preservation, hidden fields, bbox exclusivity,
closed bounds, `zoom_in`/empty outcomes, ordered detail, withheld
`404`s, connectivity direction, evidence links, envelope/cap, and
plain-language errors (spec SC-001–SC-008).

## Done when

All six steps succeed, the automated suite is green, and review
confirms no schedule fields, no provenance, and no masters appear
in any response (Principles V, VIII).

