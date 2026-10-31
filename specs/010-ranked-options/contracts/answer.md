# Contract Delta: Ranked Answer (additive to 004)

**Base**: [004 journey.md](../../004-journey-agent/contracts/journey.md), [008 selection.md](../../008-journey-selection-resolve/contracts/selection.md) | **Date**: 2026-10-31

Additive only. `status`, `answer`, `boarding_stop`, `alighting_stop`, `routes`, and `meta` are unchanged; the prose `answer` enumerates the groups so old renderers keep working.

## `ok` response gains `option_groups` and `destinations`

```json
{
  "status": "ok",
  "answer": "KSRTC: Take the Aluva — Kaloor service from Aluva to Kaloor, see /routes/17.",
  "boarding_stop": {"id": 501, "name": "Aluva"},
  "alighting_stop": {"id": 502, "name": "Kaloor"},
  "routes": [{"id": 17, "name": "Aluva — Kaloor", "evidence": "/routes/17"}],
  "option_groups": [
    {
      "operator": "KSRTC",
      "options": [
        {
          "route": {"id": 17, "name": "Aluva — Kaloor", "evidence": "/routes/17"},
          "boarding_stop": {"id": 501, "name": "Aluva"},
          "alighting_stop": {"id": 502, "name": "Kaloor"},
          "boarding_hint": "Board at Aluva",
          "stop_count": 9
        }
      ]
    }
  ],
  "destinations": [{"stop": {"id": 502, "name": "Kaloor"}, "evidence": "/routes/17"}],
  "meta": {"model": "muse-spark-1.3", "provider": "meta", "latency_ms": 1240}
}
```

| Field | Required | Meaning |
|-------|----------|---------|
| `option_groups` | yes on ranked answers | Per-operator options; unknown operator → `"Other services"` last |
| `options[]` | — | Verified only; `(stop_count, route id)` order; hint present only when supported |
| `destinations` | when destination is a place | Reachable members, matrix order, max 5, each evidence-linked |

Ordering `(operator name, stop_count, route id)` is deterministic for unchanged data. No times, durations, frequencies, or transfers appear anywhere.
