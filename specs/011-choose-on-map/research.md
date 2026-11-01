# Research: Choose on the Map

**Feature**: [spec.md](spec.md) | **Date**: 2026-10-31 | **Branch**: `011-choose-on-map`

No NEEDS CLARIFICATION remained: the requester fixed the slice (React Leaflet `MapView` + `JourneyPanel`, backend bbox from 009 groups; on `disambiguate` compute bbox from `candidates` plus `groups`, `fitBounds`, pins with selected state, buttons send IDs per 008 protocol; `none of these` clears context to a fresh question; geolocation opt-in only, default off, never auto-sent; bbox/IDs/opt-out tests). Each decision below records what was chosen, why, and what was set aside.

## Decision: Compute the fitted bbox client-side from candidate coordinates

- **Decision**: `JourneyPanel` derives the fitted bounds from candidate `lat`/`lon` (backend adds them additively to `disambiguate` candidates; 009 group payloads already carry `bbox`) and hands `{bounds, stops}` to the map via an `onShowCandidates` callback prop owned by `App.jsx`.
- **Rationale**: The client already renders the choice; deriving bounds locally keeps one source of truth for what is shown and avoids a backend viewport endpoint. Backend change is two additive fields, consistent with the 008 additive-only policy.
- **Alternatives considered**: Backend-computed viewport endpoint (rejected — new endpoint for presentational math; stateless boundary stays clean); reusing the area-search bbox (rejected — that box reflects the visible map, not the candidates).

## Decision: `MapView` gains `fitBounds` + `highlightIds` props; marker/selection core untouched

- **Decision**: New optional props only: `fitBounds={{south,west,north,east}|null}` (effect calls `map.fitBounds` once per change) and `highlightIds=[]` (amber candidate style distinct from the selected-stop style). Existing `markers`/`selectedId`/`onSelectStop` behaviour unchanged; tile-failure handling unchanged (text list is always present, satisfying FR-007).
- **Rationale**: Additive props keep the Leaflet adapter reviewable and leave the 005 area-search flow intact; distinct highlight satisfies FR-002 without restyling ordinary stops.
- **Alternatives considered**: Driving the map imperatively via ref (rejected — prop-driven fits the existing `MapView` contract and is testable without Leaflet); restyling all markers during choice (rejected — ordinary stops must stay recognizable).

## Decision: Pin taps reuse the 008 selection protocol byte-for-byte

- **Decision**: Tapping a candidate pin calls the same `choose(candidate, payload)` path as the list buttons: full IDs + `slot`/`resolved`/`slots`, preserved history. No new payload shape.
- **Rationale**: One resolution path means the 008 fast-path, both-ends, and invalid-pick handling apply identically to map and list picks; nothing new to verify server-side.
- **Alternatives considered**: A separate map-pick payload (rejected — duplicates validation and risks divergence).

## Decision: `none of these` clears context and re-asks fresh

- **Decision**: The action resets the panel to a fresh question state (`history: []`, `context: {}`) with guided rephrase help, exactly as if the passenger typed a new question; the stale candidate list never leaks (008 FR-010 machinery).
- **Rationale**: Reuses the proven fresh-question path instead of inventing a retry protocol; bounded by construction.
- **Alternatives considered**: A dedicated retry context (rejected — new state machine for what a fresh ask already does).

## Decision: Decline is per-exchange, map auto-shows every time

- **Decision**: A dismiss control hides map help for the current exchange only; every new same-name list auto-shows the helper again per the revised spec. Default is map shown.
- **Rationale**: Matches the reviewer decision (auto-show for all users); per-exchange scope avoids a persistence/preference store (constitution minimal-data posture).
- **Alternatives considered**: Persistent preference (rejected — storage + settings UI for a dismiss button); default-hidden (rejected — contradicts the auto-show rule).

## Decision: Geolocation is explicit opt-in, default off, never sent

- **Decision**: 011 adds no automatic geolocation calls. An explicit opt-in control (default off) is the only path that may center the map on the user; coordinates are never attached to journey payloads.
- **Rationale**: Constitution minimal-data posture; unfamiliar users need geography of the *candidates*, not their own position. Tests assert opt-out sends no coords and never invokes the geolocation API.
- **Alternatives considered**: Auto-locate on choice (rejected — privacy violation and irrelevant to candidate geography); no control at all (rejected — the brief requires the gated opt-in to exist).
