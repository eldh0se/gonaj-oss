# Quickstart: Place Groups for Same-Named Stops

**Feature**: [spec.md](spec.md) | **Contracts**: [contracts/places.md](contracts/places.md) | **Data model**: [data-model.md](data-model.md)

Validates the tools-only slice: `search_places` groups a duplicated name into tight place clusters with spread and route hints; `find_routes_matrix` keeps only travelling-order pairs.

## Prerequisites

- Backend deps installed (`backend/requirements.txt`); Postgres running (Docker `gonaj-oss-db-1` or local).
- `DJANGO_SECRET_KEY` set (any dev value); no model key needed (pure functions, no model calls).

## Run the gates

```bash
# backend — place-group tests alongside the existing suites
python backend/manage.py test apps.journey apps.transport tests
```

Expected: full suite green, including the new Kaloor tests (2 groups from one shared name; matrix drops the opposite-direction pair).

## Manual validation (Django shell)

```bash
python backend/manage.py shell
```

```python
from apps.journey import tools
out = tools.search_places(query="Kaloor")
[(g["key"], g["label"], len(g["members"]), round(g["spread_m"], 1), g["route_count"]) for g in out["groups"]]
m = tools.find_routes_matrix(from_ids=[501], to_ids=[501, 502])
[(p["from_stop_id"], p["to_stop_id"], len(p["routes"])) for p in m["pairs"]]
```

## What good looks like

- One shared name yields one group per tight cluster (far-apart same names split, e.g. 7 `Kaloor` stops → 2 groups), each with `spread_m` in meters and route hints.
- The matrix contains `(A, B)` but never `(B, A)` for a one-direction route; every route carries a `/routes/:id` evidence address.
- Oversized bbox returns `zoom_in` with zero groups; unknown names return `empty`; mixed/blank arguments error like `search_stops`.
