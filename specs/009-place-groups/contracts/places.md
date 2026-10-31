# Contract: Place Shapes (endpoint-ready, tools-only in 009)

**Base**: [003 stops list](../../003-read-map-api/contracts/) for `zoom_in`/`empty` semantics, [004 journey.md](../../004-journey-agent/contracts/journey.md) for evidence addresses | **Date**: 2026-10-31

009 ships no endpoint and no model tool; these shapes are the return contracts of `search_places` / `find_routes_matrix` in `backend/apps/journey/tools.py`, written so a future `GET /api/v1/places/` can adopt them unchanged.

## `search_places(query=None, bbox=None)`

Exactly one argument required. Oversized bbox → `{"ok": True, "status": "zoom_in", "groups": []}`. No matches → `{"ok": True, "status": "empty", "groups": []}`. Both/neither given → `{"ok": False, "error": ...}` (mirrors `search_stops`).

```json
{
  "ok": true,
  "status": "ok",
  "groups": [
    {
      "key": "kaloor#1",
      "label": "Kaloor",
      "center": {"lat": 9.99, "lon": 76.29},
      "bbox": {"min_lat": 9.98, "min_lon": 76.28, "max_lat": 9.99, "max_lon": 76.29},
      "spread_m": 42.5,
      "members": [{"id": 612, "name": "Kaloor", "lat": 9.99, "lon": 76.29}],
      "route_count": 3,
      "routes": [{"id": 17, "name": "Aluva — Kaloor"}]
    }
  ]
}
```

| Field | Type | Meaning |
|-------|------|---------|
| `key` | string | Stable group identity within unchanged data |
| `label` | string | Display place name |
| `center` | object | Centroid lat/lon |
| `bbox` | object | Member bounds |
| `spread_m` | number | Max pairwise member distance, meters (`0` for singles) |
| `members` | array | `{id, name, lat, lon}` per member, `(name, id)` order |
| `route_count` | integer | Exact distinct servable-route total |
| `routes` | array | `{id, name}` by `(name, id)`, first 10 |

## `find_routes_matrix(from_ids, to_ids)`

```json
{
  "ok": true,
  "pairs": [
    {
      "from_stop_id": 501,
      "to_stop_id": 502,
      "routes": [{"id": 17, "name": "Aluva — Kaloor", "evidence": "/routes/17"}]
    }
  ]
}
```

Rules: equal-id pairs are skipped; unknown ids error like `find_routes`; only pairs with ≥1 travelling-order direct route appear; opposite-direction pairs are absent, never empty.
