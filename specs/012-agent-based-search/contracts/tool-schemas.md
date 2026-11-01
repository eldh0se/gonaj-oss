# Contract: Agent Tool Schemas (012 additions)

**Base**: [004 journey.md](../../004-journey-agent/contracts/journey.md) for the
agent envelope, [009 places.md](../../009-place-groups/contracts/places.md)
for `search_places`/`find_routes_matrix` return shapes | **Date**: 2026-11-01

012 promotes two existing tools to model-callable and adds two new ones. All
four are read-only, MCP-compatible JSON schemas in
`backend/apps/journey/tools.py:TOOL_SCHEMAS`, exposed to the model via
`to_openai_tools()` and executed via `_TOOL_FUNCTIONS` + `execute_tool`
(which records every call in `tools_used` for the 007 audit log — no extra
audit rule needed). Return convention (unchanged): `{"ok": True, ...}` or
`{"ok": False, "error": ...}`; never raise.

## Promoted, no logic change

### `search_places(query?, bbox?)`

Exactly one of `query` / `bbox` (mirrors `search_stops`). Statuses
`ok` / `empty` / `zoom_in` per 009. Return shape per 009 `places.md`
(`groups[]` with `key`, `label`, `center`, `bbox`, `spread_m`,
`members[{id,name,lat,lon}]`, `route_count`, `routes[{id,name}]`).

```json
{
  "type": "object",
  "properties": {
    "query": {"type": "string", "description": "Place-name fragment; one end of the journey question."},
    "bbox": {"type": "string", "description": "Closed bounds min_lon,min_lat,max_lon,max_lat for a map-derived end. Never combined with query."}
  },
  "required": [],
  "additionalProperties": false
}
```

### `find_routes_matrix(from_ids, to_ids, limit?)`

(Field names are `from_ids` / `to_ids`, arrays of positive integers.
`from == to` pairs skipped; opposite-direction pairs drop out; unknown ids
error — behavior per 009 `places.md` and current `tools.py`, unchanged.)

Pairs are tested in ascending member-to-member haversine order; at most
`limit` (default `MATRIX_PAIR_CAP = 200`) are tested. `truncated` reports
whether pairs went untested; `untested_from_ids` / `untested_to_ids` carry
the untested members for the fallback pick.

```json
{
  "type": "object",
  "properties": {
    "from_ids": {"type": "array", "items": {"type": "integer"}, "description": "Origin member stop ids (group members, nearest-end first)."},
    "to_ids": {"type": "array", "items": {"type": "integer"}, "description": "Destination member stop ids."},
    "limit": {"type": "integer", "description": "Maximum pairs tested, nearest first. Defaults to the pair cap (200)."}
  },
  "required": ["from_ids", "to_ids"],
  "additionalProperties": false
}
```

```json
{
  "ok": true,
  "pairs": [{"from_stop_id": 101, "to_stop_id": 612, "routes": [{"id": 17, "name": "Aluva — Kaloor", "evidence": "/routes/17"}]}],
  "truncated": false,
  "untested_from_ids": [],
  "untested_to_ids": []
}
```

## New

### `distance_m(lat1, lon1, lat2, lon2)`

Thin wrapper over the existing `_haversine_m` (`R = 6371000.0`,
SQLite-portable). Non-numeric or out-of-range coordinates →
`{"ok": False, "error": ...}`.

```json
{
  "type": "object",
  "properties": {
    "lat1": {"type": "number"}, "lon1": {"type": "number"},
    "lat2": {"type": "number"}, "lon2": {"type": "number"}
  },
  "required": ["lat1", "lon1", "lat2", "lon2"],
  "additionalProperties": false
}
```

```json
{"ok": true, "distance_m": 20.4}
```

### `nearby_stops(lat, lon, radius_m?)`

Default `radius_m = 500`; enforced maximum `2000` (above → `ok: False`).
DB bbox prefilter ± radius, then `_haversine_m` filter, ascending
`distance_m`, at most 100 stops. Created now; consumed by the next feature
(shared-location origin stays out of scope in 012).

```json
{
  "type": "object",
  "properties": {
    "lat": {"type": "number"}, "lon": {"type": "number"},
    "radius_m": {"type": "number", "description": "Search radius, default 500, maximum 2000."}
  },
  "required": ["lat", "lon"],
  "additionalProperties": false
}
```

```json
{"ok": true, "stops": [{"id": 612, "name": "Kaloor", "lat": 9.99, "lon": 76.29, "distance_m": 42.5}]}
```

## `_validate_tool_args` extensions (`agent.py`)

- `from_ids`/`to_ids`: lists of ints (non-bool), all ≥ 1; empty list →
  invalid (never executed). Optional `limit`: int ≥ 1.
- `execute_tool` records matrix pair findings (`route_id` → pair) so the
  server verifier and fallback can re-check model-cited matrix pairs.
- `distance_m`/`nearby_stops` numeric fields: `int` (non-bool) or `float`,
  finite; `lat` in [-90, 90], `lon` in [-180, 180]; `radius_m` in
  (0, 2000].
