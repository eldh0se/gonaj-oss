# Contract: Endpoint Fallback (delta vs 003)

**Feature**: [spec.md](../spec.md) | **Date**: 2026-10-29

This document records the ONLY contract change this feature
makes against
`specs/003-read-map-api/contracts/read-map-api.md`. That
document stays normative for everything not named here:
envelopes, paging, search, `zoom_in`/`empty` statuses,
throttling, errors, and the hidden-field rules.

## Changed: `origin` / `destination` value rule

Applies identically to route list items, route detail, and
connectivity results. Field names, types, and positions are
unchanged; only the value rule gains a second step:

1. Serve stored `from_text` / `to_text` when non-blank
   (null, empty, and whitespace-only count as blank).
2. Otherwise serve the endpoint stop name (first ordered
   stop for origin, last for destination), or null when the
   route has no recorded stops.

```json
{
  "id": 17,
  "name": null,
  "origin": "Ernakulam South",
  "destination": "Fort Kochi",
  "operator": "KSRTC",
  "network": null
}
```

The example above is a route with blank stored text whose
first ordered stop is "Ernakulam South" and whose last is
"Fort Kochi". A route with stored text serves it
byte-identically to before; a stop-less route serves
`"origin": null, "destination": null` as before.

## Explicitly unchanged

- No new fields, no removed fields, no renamed fields.
- No provenance, tags, OSM ids, or master objects leak
  through the fallback (the same serializer whitelist
  renders the values).
- No envelope, paging, search, throttle, or error change.
- Evidence URLs, `from_position`/`to_position`, stop
  payloads, and serving-route payloads are untouched.
