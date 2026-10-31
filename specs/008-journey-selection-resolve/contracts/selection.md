# Contract Delta: Journey Selection Resolve (additive to 004)

**Base**: [004 journey.md](../../004-journey-agent/contracts/journey.md) | **Date**: 2026-10-31

Additive only. No fields removed, no endpoints added, no status values changed. `views.py` passes the body through; all new validation lives in `agent.py`.

## Disambiguation response gains slot identity

```json
{
  "status": "disambiguate",
  "message": "I found more than one stop called North. Which one did you mean?",
  "candidates": [{ "id": 201, "name": "North Hub", "detail": "നോർത്ത് ഹബ്" }],
  "slot": "from",
  "resolved": { "id": 11, "name": "Ernakulam South" },
  "offered_ids": [201, 312]
}
```

| Field | Required | Meaning |
|-------|----------|---------|
| `slot` | yes, when ambiguous | Which end is being asked: `from` or `to` |
| `resolved` | when the other end is fixed | The already-resolved stop `{id, name}` |
| `offered_ids` | yes, when ambiguous | Candidate IDs offered for this slot |
| `detail` (per candidate) | no, additive | Distinguishing detail: `name_ml` when present, else rounded `lat,lon`; rendered after the name |

Both-ends-ambiguous responses additionally carry `slots: {from_ids, to_ids}` and `surviving_context: {other_end_ids}` instead of a bare `(None, None)`.

## Selection reply carries IDs, slot, and surviving context

```json
{
  "question": "North Hub",
  "history": [{ "role": "user", "content": "How do I get from North to South?" }],
  "context": {
    "candidate_stop_ids": [201, 312],
    "selected_stop_id": 201,
    "slot": "from",
    "resolved": { "id": 11, "name": "Ernakulam South" }
  }
}
```

| Field | Required | Meaning |
|-------|----------|---------|
| `question` | yes | Display text of the pick; identity comes from IDs, not this string |
| `history` | no | Original question preserved (frontend must not force `[]`) |
| `context.candidate_stop_ids` | yes | IDs offered; `selected_stop_id` must be a member |
| `context.selected_stop_id` | yes | Integer pick; forged/non-member IDs refuse safely |
| `context.slot` | yes | `from` or `to` |
| `context.resolved` | when the other end is known | Fixed other end; `id` must be integer |

Invalid selections (forged ID, missing/non-int `resolved`, bad `slot`) receive a safe `refuse` with no invented stops or routes.

Typed picks need no wire change: when the passenger types a name or position instead of clicking, the frontend resends the previous `context` (with `candidate_stop_ids`, `slot`, `resolved`) and the new `question` text; the server derives `selected_stop_id` by unambiguous text match (case-insensitive exact name matching exactly one candidate, or a 1-based position / ordinal matching exactly one slot entry). Text matching zero or more than one candidate is invalid.

## Selection fast-path response meta

```json
{ "meta": { "model": "none", "provider": "local-fallback", "resolution": "selection", "latency_ms": 42 } }
```

`resolution: "selection"` distinguishes a local pick-resolution from the model-outage fallback, which keeps the existing `model:none / provider:local-fallback` shape with no `resolution` key. `tools_used` audit records the direct `find_routes` call.
