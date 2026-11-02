# Contract: Group-First Answer Shape

**Base**: [004 journey.md](../../004-journey-agent/contracts/journey.md) for
the payload envelope, [tool-schemas.md](./tool-schemas.md) for the tools |
**Date**: 2026-11-01

## Per-route block

Each cited route is one block: the existing `rank_pairs` option
(`route{id,name,evidence}`, `boarding_stop{id,name}`, `alighting_stop{id,name}`,
`stop_count`, `boarding_hint`) extended with walk notes:

```json
{
  "route": {"id": 17, "name": "Aluva — Kaloor", "evidence": "/routes/17"},
  "boarding_stop": {"id": 101, "name": "Aluva"},
  "alighting_stop": {"id": 612, "name": "Kaloor"},
  "also_nearby_boarding": [{"id": 102, "name": "Aluva East", "walk_m": 60}],
  "also_nearby": [{"id": 613, "name": "Kaloor", "walk_m": 20}],
  "overflow_nearby_boarding": 0,
  "overflow_nearby": 0,
  "stop_count": 14
}
```

Rules: `also_nearby*` holds at most 3 nearest mates per end
(`d <= 150m` inclusive via `distance_m`); `overflow_nearby_boarding` /
`overflow_nearby` count further qualifying mates per end
(`plus {N} more within 150m` in prose). `walk_m` is whole meters, half up. Options group by operator and order by `(stop_count, route_id)`
(existing `_rank_pairs` — reused). At most 5 destinations are cited, ranked
operator group → stop count → route id (clarify outcome B); further
destinations fold into the existing `rank_pairs` overflow prose
(`Plus {extra} more drop-off options at this place.`).

## Prose template (research Decision 3)

Single route:
`Take the {route_name} service from {boarding_name} to {alighting_name}, see /routes/{route_id}.`
plus, per end with mates:
` Also near {end_name}: {mate_name} ({walk_m}m walk)[, ...][ plus {N} more within 150m].`

Multi-destination answers join one block per destination following the
existing `rank_pairs` sentence pattern (`{operator}: Take the ...`).
The draft still passes the unchanged server verifier (`/routes/(\d+)`
extraction, `_FORBIDDEN_SHAPED`, `pos_from < pos_to` re-check, one repair
retry, then refuse).

## Fallback selection (clarify outcome C, FR-007/FR-012)

- Every tested pair fails + place matched → polite `NO_DIRECT` refusal.
- Pairs untested (200-pair cap) or place never matched (`empty`) → map/list
  pick payload (`slot`, `offered_ids`, `resolved`, `slots`) — pick selects a
  member id only and re-enters the same matrix flow.
- `zoom_in` → narrow-the-area request (or map prompt); never a silent
  substitution.
