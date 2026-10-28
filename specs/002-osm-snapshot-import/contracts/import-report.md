# Contract: Import Report JSON

**Feature**: [spec.md](../spec.md) | **Date**: 2026-10-29

Machine-readable artifact written to `--report-path` on every completed
or aborted run. Consumers: CI gates, reviewer tooling, drift detection
across runs.

## Shape

```json
{
  "label": "gcda",
  "recipe_ref": "data/osm/gcda/osm-extraction.md",
  "snapshot": {
    "label": "gcda",
    "source_timestamps": {
      "osm_gcda_routes.json": "2026-09-14T06:38:49Z"
    },
    "retrieved_at": "2026-09-14T07:00:00Z",
    "imported_at": "2026-10-29T03:00:00+05:30"
  },
  "run": {
    "started_at": "2026-10-29T03:00:00+05:30",
    "finished_at": "2026-10-29T03:04:12+05:30",
    "outcome": "succeeded"
  },
  "counts": {
    "stop": { "inserted": 3278, "updated": 0, "unchanged": 0 },
    "route": { "inserted": 927, "updated": 0, "unchanged": 0 },
    "route_master": { "inserted": 465, "updated": 0, "unchanged": 0 },
    "route_stop_membership": { "inserted": 46084, "updated": 0, "unchanged": 0 },
    "route_master_membership": { "inserted": 917, "updated": 0, "unchanged": 0 }
  },
  "anomalies": [
    {
      "severity": "fatal",
      "code": "CHILD_REF_MISSING",
      "entity": { "osm_type": "relation", "osm_id": 13657355 },
      "detail": "referenced by master 13657357, absent from snapshot"
    }
  ]
}
```

## Field rules

- `outcome` is `succeeded` or `aborted`; `aborted` runs carry the
  file-level fatal anomaly and zero counts.
- `counts` covers every imported entity; a rerun of an unchanged
  snapshot MUST show zeros across inserted/updated.
- Every `anomalies[]` entry carries `severity` (`fatal`/`warning`/
  `info`) and a `code` from the closed set; `entity` is null for
  file-level anomalies.
- Timestamps are ISO-8601 with offset; missing source timestamps are
  omitted keys, never fabricated values.
