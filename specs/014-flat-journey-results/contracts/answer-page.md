# Contract: Flat Paged Journey Answer

**Feature**: [spec.md](../spec.md) | **Date**: 2026-11-03

Delta against `specs/004-journey-agent/contracts/journey.md` and
`specs/010-ranked-options/contracts/answer.md`: successful ranked
answers return a flat paged option list instead of `option_groups`.
Disambiguate, refuse, and fallback shapes are unchanged.

## Request

`POST /api/v1/journey/` accepts two additive fields (both optional):

| Field | Type | Meaning |
|-------|------|---------|
| `page` | integer ≥ 1, default 1 | 1-based page to serve; values < 1 behave as 1 |
| `page_size` | integer, default 5, max 20 | options per page; values < 1 behave as 5, values > 20 are clamped to 20, never an error |

`question`, `history`, and `context` behave exactly as before.

## Success response — `200` (`status: "ok"`)

```json
{
  "status": "ok",
  "answer": "24 direct options; quickest: Ernakulam — Fort Kochi from Kaloor.",
  "options": [
    {
      "route": { "id": 17, "name": "Ernakulam — Fort Kochi", "evidence": "/routes/17" },
      "boarding_stop": { "id": 42, "name": "Kaloor" },
      "alighting_stop": { "id": 118, "name": "Fort Kochi" },
      "operator": "KSRTC",
      "network": "City",
      "stop_count": 9
    }
  ],
  "destinations": [],
  "page": 1,
  "page_size": 5,
  "total_options": 24,
  "total_pages": 5,
  "meta": { "model": "muse-spark-1.3", "provider": "meta", "latency_ms": 1240 }
}
```

- `options` holds only the requested page, in global relevance order (`stop_count`, then route id).
- `answer` is a page-scoped summary of at most 1000 characters; it never enumerates options.
- `option_groups` is absent. `destinations` (up to 5) and `meta` are unchanged.
- Page past the last page returns `"options": []` with the same totals.

## Frontend behavior

- One card per option: route name, boarding/alighting stops, boarding hint, walk notes, evidence link, operator.
- The answer header names the generating model ("Answer generated using \<model\>") from the response `meta`, shown only when the model is known (hidden for the local-fallback `"none"` model and for payloads without `meta`).
- The shared `Pager` (Prev/Next + "Page X of Y · N options", same as the routes/stops tabs) fetches the requested page and replaces the cards; it hides when `total_pages` is 1 and disables Prev/Next at the ends.
- Evidence links use client-side navigation: opening a route and closing its overlay keeps the journey results.
- The text filter narrows rendered cards by stop, service, and operator text on the current page only; changing page clears it, and clearing restores all cards on the current page in order.
- A filter matching nothing shows the plain empty state with the filter text preserved for clearing.

## Errors

Unchanged: plain-language `400` for bad questions, `disambiguate` for ambiguous stops, `refuse` for no direct service, local-fallback on model outage. Paging values never cause errors (clamped per the table above).
