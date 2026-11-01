# Contract: Map Choice Props and Payloads

**Base**: [008 selection](../../008-journey-selection-resolve/contracts/selection.md) (payload identity), [004 journey](../../004-journey-agent/contracts/journey.md) (additive policy) | **Date**: 2026-10-31

## `MapView` additions (optional props, additive)

```javascript
<MapView
  markers={[{ id, lat, lon }]}
  highlightIds={[612, 613]}   // candidate pins: amber, distinct from selectedId
  fitBounds={{ south, west, north, east } | null}  // applied once per change
  selectedId={612}
  onSelectStop={(marker) => choose(marker, payload)}
/>
```

| Prop | Type | Meaning |
|------|------|---------|
| `highlightIds` | `int[]` | Candidate pins; amber style, distinct from the selected-stop style |
| `fitBounds` | `object\|null` | Candidate bounds; `map.fitBounds` runs once per value change; `null` clears the candidate view |

## `JourneyPanel` additions (props in, unchanged REST out)

```javascript
<JourneyPanel
  onShowCandidates={(view | null) => {}}
/>
```

- `view = { bounds: {south, west, north, east}, stops: [CandidatePin] }`, computed from `candidates` (+ 009 `groups[].bbox` when present) on every `disambiguate`.
- `null` on answer, refusal, decline, or new question.
- Pin taps call the existing `choose(candidate, payload)` — byte-identical 008 payloads.
- `None of these` resets to `history: []`, `context: {}` and re-asks as a fresh question.
- Dismiss sets per-exchange `mapHelpDismissed`; auto-show returns on the next same-name list.

## Backend delta (additive, two fields)

`disambiguate` candidates gain `lat`/`lon` alongside `id`/`name`/`detail`:

```json
{ "id": 612, "name": "Kaloor", "lat": 9.99, "lon": 76.29, "detail": "10.0500,76.3000" }
```

## Payload rules

- Journey `POST /api/v1/journey/` bodies from opt-out sessions MUST contain no coordinates; the geolocation API MUST NOT be invoked unless the explicit opt-in control is enabled (default off).
