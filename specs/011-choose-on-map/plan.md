# Implementation Plan: Choose on the Map

**Branch**: `011-choose-on-map` | **Date**: 2026-10-31 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/011-choose-on-map/spec.md` plus the requester plan-time slice (React Leaflet `MapView` + `JourneyPanel`, backend bbox from 009 groups; on `disambiguate` compute bbox from `candidates` plus `groups`, `fitBounds`, pins with selected state, buttons send IDs per 008 protocol; `none of these` clears context to a fresh question; geolocation opt-in only, default off, never auto-sent; bbox/IDs/opt-out tests).

## Summary

Text lists cannot convey side-of-road geography. On every `disambiguate` response, `JourneyPanel` computes a fitted bbox from candidate coordinates (plus 009 group bboxes when present) and hands it to the map via `onShowCandidates`; `MapView` gains additive `fitBounds`/`highlightIds` props (amber candidate pins, existing selection style untouched); pin taps reuse the byte-identical 008 `choose` path; a `none of these` action resets to a fresh question; a per-exchange dismiss hides map help. Backend adds `lat`/`lon` to `disambiguate` candidates (two additive fields). Geolocation stays gated behind an explicit opt-in defaulting to off and is never sent. See [research.md](research.md) for decisions and rationale.

## Technical Context

**Language/Version**: React + JSX + Vite + Vitest (frontend); Python 3.13, Django 5.2 (two additive backend fields).

**Primary Dependencies**: Existing Leaflet `MapView` adapter (005), `JourneyPanel` (004/008), 009 group `bbox`. No new packages.

**Storage**: No schema change; decline state is per-exchange component state, never persisted.

**Testing**: Vitest component tests with mocked Leaflet (`npm test -- --run`); Django suite for candidate coordinate fields (`python backend/manage.py test apps.journey apps.transport tests`).

**Target Platform**: Responsive web frontend + existing deployable backend.

**Project Type**: Frontend feature slice with a two-field additive backend delta, wired in the existing `App.jsx` composition.

**Performance Goals**: Bounds computed over at most tens of candidates; one `fitBounds` per disambiguation; no extra network calls (coordinates ride the existing payload).

**Constraints**: Additive props/fields only; 008 selection payloads byte-identical for pins and buttons; no coordinates in journey payloads when opted out; geolocation API never invoked unless explicitly opted in; tile failure still falls back to the text list.

**Scale/Scope**: MVP audience. Two component diffs (`MapView`, `JourneyPanel`), one `App.jsx` wiring, two backend fields, 4–6 frontend tests + 1–2 backend tests.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I (MVP validation first)**: PASS — map choosing directly serves unfamiliar users facing same-name stops.
- **II (Read-only public product)**: PASS — no new mutation surface; read-only map + existing endpoints.
- **III (No accounts, minimal data)**: PASS — per-exchange dismiss state only; geolocation opt-in default off, never sent; no tracking.
- **IV (Monorepo separation)**: PASS — components talk via props; REST boundary unchanged.
- **V (App-owned GTFS-inspired data + provenance)**: PASS — candidate coordinates come from canonical stops.
- **VI (Simple synchronous stack)**: PASS — no new infra or services.
- **VII (Django Admin operations)**: PASS — no admin/data-model change.
- **VIII (Schedule gates)**: PASS — no times/schedules involved.
- **IX (Meta AI integration)**: PASS — no model calls, prompts, or tool changes; selection protocol untouched.

*Post-design re-check (Phase 1 complete): PASS — data-model adds no tables, contracts add props/fields only, quickstart introduces no runtime behaviour.*

## Project Structure

### Documentation (this feature)

```text
specs/011-choose-on-map/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── map-choice.md    # prop/payload rules (MapView, JourneyPanel, backend delta)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
frontend/
├── src/
│   ├── App.jsx                  # onShowCandidates wiring: candidate view state → MapView
│   └── components/
│       ├── MapView.jsx          # + fitBounds/highlightIds props (additive)
│       ├── MapView.test.jsx     # + fit/highlight/opt-in tests
│       ├── JourneyPanel.jsx     # bbox compute, pin choose, none-of-these, dismiss, opt-in gate
│       └── JourneyPanel.test.jsx# + bbox/IDs/opt-out tests
backend/
└── apps/
    └── journey/
        ├── agent.py             # + lat/lon on disambiguate candidates (additive)
        └── tests/
            └── test_journey.py  # + candidate coordinate assertions
```

**Structure Decision**: Frontend-led slice in the existing 005 composition (`App.jsx` owns the candidate view; `MapView` stays a prop-driven adapter); backend delta is two additive fields on the existing disambiguation payloads.

## Complexity Tracking

No constitution violations. No entries.

## Implementation notes (for /speckit-tasks)

1. Backend `agent.py`: add `lat`/`lon` to `_candidate_entry` outputs (both model-loop enriched and partial-prompt builders); assert in `test_journey.py`.
2. `MapView.jsx`: `fitBounds` effect (once per change) + `highlightIds` amber style; `App.jsx`: candidate-view state, `onShowCandidates` wiring, explicit geolocation opt-in control defaulting to off (never attached to journey payloads).
3. `JourneyPanel.jsx`: bbox from `candidates` (+ `groups[].bbox` when present), `choose` reuse for pins, `none of these` → fresh ask (`history: []`, `context: {}`), per-exchange dismiss, auto-show on every same-name list.
4. Tests: frontend bbox-matches-candidates, choose-sends-IDs (pin ≡ button payloads), opt-out-sends-no-coords (no geolocation call); backend candidate coordinate assertions; regression `npm test -- --run` + `manage.py test apps.journey apps.transport tests`.
