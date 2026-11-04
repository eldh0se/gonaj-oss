# Quickstart: 016-frontend-ux-polish

**Feature**: 016-frontend-ux-polish | **Date**: 2026-11-04

## Prerequisites

- `frontend/` deps installed; `npm test` (vitest) green on main.
- Backend running (or fetch stubs) for routes/stops/journey endpoints — unchanged.

## Validate

1. **Scoped search**: `npm test -- ResultsList` + open the app; Journey tab has no search box; Routes/Stops tabs each search + page independently; sticky header intact.
2. **Mobile cap**: devtools 390px width; open a route → sheet ≤ 50% viewport, internal scroll, map interactive; close → previous tab content back; desktop width → dock still `min(400px,100%)`.
3. **Route focus**: open a route from Journey and from Routes; only its polyline + stops show, origin/destination distinct + labeled; close → area markers return. Open a stop card → map centers, markers stay.
4. **Dictate**: quick-click Dictate → inline press-and-hold explanation, no recording; hold → pulsing dot + `Listening… release to send` live region + Ask disabled; release → transcribe fills the question.
5. **Mutual clear**: type a question, then pick From/To → ask state cleared; set direct + submit ask → direct cleared; try mid-selection both ways.
6. **Ask lock**: submit ask → direct controls disabled + Stop visible; Stop → idle with question intact, nothing fired.
7. **Version**: `npm run build` → footer shows `v0.1.0+<sha> · built <UTC>`; `npm test -- App` covers the `v0.1.0` fallback.

## Full suite

- `cd frontend && npm test` — all suites green, no desktop visual regression.
