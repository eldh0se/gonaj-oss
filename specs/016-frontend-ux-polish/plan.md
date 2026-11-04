# Implementation Plan: 016-frontend-ux-polish

**Branch**: `016-frontend-ux-polish` | **Date**: 2026-11-04 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/016-frontend-ux-polish/spec.md` — frontend journey/search/map UX polish + visible build version (7 stories, FR-001…FR-009).

## Summary

Move the debounced `SearchBox` into the Routes/Stops tab panels only, cap the mobile overlay at 50dvh with close-restores-tabs, wire route-focus (hide area markers, fit bounds, distinct origin/destination) vs stop-centering (markers stay) through existing `MapView` props, show permanent stop-name labels once the in-bounds stop count drops to a readable handful (≤24 after phone field feedback, area and focus alike), add press-and-hold dictate hint + recording state, mutual ask/direct clearing with ask-loading lock + Stop abort, and a build-time-injected footer version — all frontend-only, verified by vitest per the UI contracts.

## Technical Context

**Language/Version**: JavaScript (JSX) + React 18.3.1 (constitution v1.4.0 permits JSX where the scaffold sets precedent)

**Primary Dependencies**: React 18, react-router-dom 6, Leaflet 1.9.4, Vite 6 (build defines), vitest 2 + Testing Library + jsdom

**Storage**: N/A (no backend change; version from build-time defines, not an API)

**Testing**: vitest (`cd frontend && npm test`); new/updated suites per story Independent Tests: `ResultsList`, `App` (overlay/focus/footer), `JourneyPanel` (dictate/mutual-clear/lock), `MapView` (focus props, permanent labels), `RouteOverlay` (cap/close), `App.css` media rule

**Target Platform**: Responsive web frontend (mobile ≤48rem + desktop); no native app

**Project Type**: Web application — frontend-only change (`frontend/src/`, `frontend/vite.config.js`)

**Performance Goals**: No new fetches; same search request count (one shared query state); map focus reuses existing fitBounds/setView effects

**Constraints**:
- No backend change; no new dependencies unless required (none foreseen)
- Keep debounced search (300ms), `Pager`, loading/no-match/error states byte-for-byte in behavior
- Desktop overlay `min(400px,100%)` unchanged; only the `max-width:48rem` block changes
- Accessibility: tabs keep `role=tab` semantics; recording uses `role=status`/`aria-live`; origin/destination markers get accessible labels; pulsing dot honors `prefers-reduced-motion`; focus management on overlay open/close
- Version via build-time defines `__APP_VERSION__`/`__APP_SHA__`/`__APP_BUILT_AT__` with `v{version}` fallback in `footer.gonaj-version[data-testid=app-version]`

**Scale/Scope**: 7 stories across 6 component files + CSS + Vite config; ~7 test suites

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- I. MVP Validation: PASS — route/stop discovery + journey answers are the MVP question; polish removes friction from exactly that.
- II. Read-Only + Feedback: PASS — no dataset mutation, no feedback change.
- III. No accounts/tracking: PASS — no analytics, no storage added.
- IV. Monorepo separation: PASS — frontend-only, REST usage unchanged.
- V. Provenance: PASS — no data-model change.
- VI. Simple stack: PASS — no new services, deps, or engines.
- VII. Admin: N/A — no data ops.
- VIII. Schedule gating: PASS — no schedule content touched.
- IX. Meta AI: PASS — journey/transcribe call paths unchanged; version label is build metadata, not an AI claim. (Existing answer cards already carry the "can make mistakes" disclaimer + model line; untouched.)
- Stack (JSX): PASS — scaffold precedent per v1.4.0 amendment; no conversion in scope.

Post-design re-check: no new gates tripped — research/data-model/contracts/quickstart introduce no backend, deps, tracking, or schedule content.

## Project Structure

### Documentation (this feature)

```text
specs/016-frontend-ux-polish/
├── spec.md              # Feature specification
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── ui.md            # Phase 1 output (UI-level contracts; no REST change)
└── tasks.md             # Phase 2 output (/speckit-tasks command — NOT created here)
```

### Source Code (repository root)

```text
frontend/
├── src/
│   ├── App.jsx                 # FR-001: drop global SearchBox; FR-004/009: focus wiring; FR-008: footer
│   ├── App.css                 # FR-003: 48rem overlay cap 50dvh; version + recording styles
│   ├── vite.config.js          # FR-008: __APP_VERSION__/__APP_SHA__/__APP_BUILT_AT__ defines
│   ├── components/
│   │   ├── ResultsList.jsx     # FR-001/002: per-tab SearchBox; FR-003: close-restores-tabs
│   │   ├── SearchBox.jsx       # unchanged behavior (reused per tab)
│   │   ├── RouteOverlay.jsx    # FR-003: capped scrollable sheet, no collapse control
│   │   ├── MapView.jsx         # FR-004/009: distinct origin/destination markers (area markers prop-driven)
│   │   └── JourneyPanel.jsx    # FR-005/006/007: hint, tap-vs-hold, mutual clear, lock + Stop
└── tests (colocated *.test.jsx per component + App.test.jsx)
```

**Structure Decision**: Frontend-only change inside the existing `frontend/src` layout; existing colocated `*.test.jsx` suites extended per story. No backend, no new directories.

## Complexity Tracking

> No constitution violations — table intentionally empty.
