# Quickstart: Choose on the Map

**Feature**: [spec.md](spec.md) | **Contracts**: [contracts/map-choice.md](contracts/map-choice.md) | **Data model**: [data-model.md](data-model.md)

Validates map-assisted choosing end to end: auto-fit, distinct pins, pin-tap resolution, none-of-these retry, decline, and geolocation opt-out.

## Prerequisites

- Frontend deps installed; backend running with Postgres; `DJANGO_SECRET_KEY` set.
- Dev servers: backend plus `npm run dev` (or the preview bundle under test).

## Run the gates

```bash
# frontend — map-choice tests alongside the existing suites
npm test -- --run
```

```bash
# backend — candidate coordinate fields alongside the existing suites
python backend/manage.py test apps.journey apps.transport tests
```

Expected: both suites green, including bbox-matches-candidates, choose-sends-IDs, and opt-out-sends-no-coords tests.

## Manual validation (dev servers running)

1. Ask an ambiguous journey (e.g. "How do I get from North to South?") → map pans/zooms to fit every candidate pin; candidate pins render amber, ordinary stops unchanged.
2. Tap a candidate pin → journey resolves to that exact stop (same result as the text button).
3. Answer `none of these` → panel resets to a fresh question with rephrase help; stale candidates do not leak.
4. Dismiss map help → text list completes the journey with no map re-prompts; ask again → helper auto-shows.
5. With geolocation never enabled → confirm no location prompt appears and journey payloads carry no coordinates.

## What good looks like

- First display always fits all pins; pin taps and list buttons are interchangeable.
- Decline is respected per exchange and auto-show returns on the next list.
- Opt-out sessions invoke no geolocation API and send no coordinates.
