# Read Map API — public usage guide

Public read-only transport API for passengers and AI tools.
Part of `specs/003-read-map-api`; the normative contract is
`specs/003-read-map-api/contracts/read-map-api.md`.

## Base and access

All reads live under `/api/v1/`. No login, no accounts, no API
keys, and no tracking identifiers of any kind. Every request is a
`GET`; anything else is refused with a plain-language message.

Basic abuse protection applies per client IP across all five reads
combined: 180 requests/minute and 5,000/day. Over the limit, the
API answers `429 Too Many Requests` in the same plain-language
shape with a `Retry-After` header telling well-behaved clients how
long to wait. Counters are hashed and expire with their window —
raw addresses are never stored.

## Endpoints

| Method & path | What it answers |
|---|---|
| `GET /api/v1/routes/?search=&operator=&network=` | Browse (blank search) or search routes by name, origin, destination, or served stop name; exact operator/network filters narrow the result |
| `GET /api/v1/routes/{id}/` | One route with its stops in travelling order; origin and terminus marked |
| `GET /api/v1/stops/?search=` | Find stops by name fragment |
| `GET /api/v1/stops/?bbox=min_lon,min_lat,max_lon,max_lat` | Find stops inside a map area (closed bounds); search and bbox are alternatives, never combined |
| `GET /api/v1/stops/{id}/` | One stop with coordinates and serving routes |
| `GET /api/v1/connectivity/?from=&to=` | Direct routes serving both stops in order, each linking to its route detail as evidence |

No times, durations, transfers, or schedules appear anywhere —
schedule data does not exist in this phase. Source tags,
provenance records, and grouping records are never exposed.

## Map-area behaviour

- A normal area returns `status: "ok"` with the matching stops.
- An area too large to list returns `status: "zoom_in"` with zero
  stops and guidance to zoom in — never a partial list.
- A valid area with no stops returns `status: "empty"`, an
  explicit empty result, not an error.

## List envelope

Every list uses the same shape: `count`, `results`,
`total_pages`, `current_page`, `page_size`. Pages default to 20
items and never exceed 100. Errors are one plain-language sentence
telling the caller what went wrong and what to try next.

## Setup note for operators

Before serving traffic, create the throttle-counter table in the
application database:

```sh
cd backend
./manage.py createcachetable
```

This table holds only hashed, expiring counters — no personal
data. See `docs/setup-backend.md` for the general backend setup.
