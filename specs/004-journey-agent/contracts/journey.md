# Contract: Journey Endpoint

**Feature**: [spec.md](../spec.md) | **Date**: 2026-10-29

`POST /api/v1/journey/` — ask in everyday words, receive an
evidence-grounded direct-service answer, a disambiguation prompt,
or an honest refusal. Unauthenticated and untracked like every
public read (spec FR-002/FR-003 as applied here: no login, no
per-user memory). Throttled with the other reads (180/minute,
5,000/day per IP; plain-language 429 with `Retry-After`).
GET and other verbs on this path are refused (`405`, shared
plain-language shape).

## Request

```json
{
  "question": "How do I get from Ernakulam South to Fort Kochi?",
  "history": [],
  "context": {}
}
```

| Field | Required | Meaning |
|-------|----------|---------|
| `question` | yes | Typed text or edited transcript. Blank or whitespace = ask-again prompt, never a model call. |
| `history` | no | Prior turns for follow-ups, at most the last 6; extras are ignored. Used only for this request. |
| `context` | no | Disambiguation state from a previous prompt, e.g. `{"candidate_stop_ids": [101, 205]}`. Stale ids are treated as unknown stops. |

Invalid JSON, missing `question`, or a non-object body returns
the plain-language `400`.

## Success response — `200`, answer

```json
{
  "status": "ok",
  "answer": "Take the Ernakulam — Fort Kochi service from Ernakulam South to Fort Kochi.",
  "boarding_stop": { "id": 101, "name": "Ernakulam South" },
  "alighting_stop": { "id": 118, "name": "Fort Kochi" },
  "routes": [
    { "id": 17, "name": "Ernakulam — Fort Kochi", "evidence": "/routes/17" }
  ],
  "meta": { "model": "muse-spark-1.3", "provider": "meta", "latency_ms": 1240 }
}
```

- `answer` is everyday language naming the resolved stops and
  the direct service. It contains no times, durations,
  frequencies, or transfers — the verifier guarantees it.
- Every entry in `routes` was confirmed to serve both stops in
  travelling order; every `evidence` URL is a frontend
  `/routes/:id` address (the 005 map page with the detail
  overlay), never an `/api/v1/` URL.
- `meta.model` is the declared model (or `none` for the
  fallback), `meta.provider` its provider (or
  `local-fallback`), `meta.latency_ms` the measured producing
  latency.

## Disambiguation response — `200`

```json
{
  "status": "disambiguate",
  "message": "I found more than one stop called North. Which one did you mean?",
  "candidates": [
    { "id": 201, "name": "North Hub" },
    { "id": 312, "name": "North Edge" }
  ],
  "meta": { "model": "muse-spark-1.3", "provider": "meta", "latency_ms": 480 }
}
```

No journey answer is given yet. The passenger replies with a
choice (as `question` naming the candidate, or `context` with
`candidate_stop_ids`); the follow-up answers for the chosen
stop or refuses honestly.

## Refusal response — `200`

```json
{
  "status": "refuse",
  "message": "I could not find a direct service between those stops.",
  "meta": { "model": "muse-spark-1.3", "provider": "meta", "latency_ms": 510 }
}
```

Returned when no direct service is known, the stop cannot be
found, the question is unclear, or the model output failed
verification. Nothing unverifiable is ever delivered alongside
it. Model outages and timeouts (after one retry) return this
shape with the cannot-answer message and fallback meta.

## Tool contracts (model-facing, MCP-compatible JSON schemas)

The model may call only these three functions. Each is
read-only over canonical tables and shares semantics with the
003 read API.

### `search_stops`

| Argument | Type | Meaning |
|----------|------|---------|
| `query` | string, optional | Name fragment (case-insensitive containment over name/name_ml) |
| `bbox` | string, optional | `min_lon,min_lat,max_lon,max_lat` (closed bounds). Never combined with `query`. |

Returns matching stops (`id`, `name`, `name_ml`, `lat`,
`lon`). Oversized areas return `zoom_in` guidance with zero
stops; empty areas return `empty`.

### `find_routes`

| Argument | Type | Meaning |
|----------|------|---------|
| `from_stop_id` | integer, required | Boarding stop id |
| `to_stop_id` | integer, required | Alighting stop id (must differ) |

Returns direct routes serving both stops in order
(`from_position < to_position`), each with `evidence` (a
frontend `/routes/:id` address).
Empty list when unconnected; error when ids are unknown.

### `get_route_detail`

| Argument | Type | Meaning |
|----------|------|---------|
| `route_id` | integer, required | Servable route id |

Returns the route with ordered stops (`position`,
`is_origin`, `is_terminus`); explicit empty list when the
servable route has no memberships; error for unknown or
withheld ids.

## Non-goals (explicitly out of contract)

- Times, timetables, frequencies, transfers, multi-leg
  journeys: never requested of the model, never returned.
- Feedback submission, record mutation, moderator actions.
- Streaming responses; one complete response per request.
- Authentication, accounts, sessions, or per-user history.

