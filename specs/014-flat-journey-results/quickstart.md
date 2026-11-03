# Quickstart: Flat Paginated Journey Results

**Feature**: `014-flat-journey-results` | **Date**: 2026-11-03

Validates the flat paged answer end to end. Backend checks run
without a model key ( StubModel / pure ranking); the frontend check
needs the dev server plus `npm run dev` (or the served build).

## Prerequisites

- Backend deps installed; Postgres running (`docs/setup-backend.md`).
- `DJANGO_SECRET_KEY` set (any dev value).
- Seed data loaded (area-to-area query needs multiple routes sharing stops).

## 1. Paged answer (stubbed)

```sh
cd backend
../.venv/bin/python manage.py test apps.journey.tests.test_ranked apps.journey.tests.test_area_search -v 1
```

Expected: green. Covers flat relevance order, `operator`/`network` carried per option, `option_groups` absent, prose ≤ 1000 chars, page slices with totals, clamping, and beyond-last-page emptiness.

## 2. Live page walk (needs seed data, no key)

```sh
curl -s -X POST http://localhost:8000/api/v1/journey/ \
  -H 'Content-Type: application/json' \
  -d '{"question": "buses from Kaloor to Fort Kochi", "page": 1, "page_size": 5}' \
  | ../.venv/bin/python -m json.tool | head -40
```

Expected: `status: "ok"`, 5 flat `options` in relevance order, `total_options` > 5, `total_pages` ≥ 2, summary prose, no `option_groups`. Repeat with `"page": 2` and confirm new option ids with no overlap.

## 3. Cards, pager, filter (needs frontend)

Run the dev server and frontend, ask an area-to-area question, and confirm: cards show route, stops, operator, and evidence link; the shared Prev/Next pager ("Page X of Y · N options") fetches each page in order and hides on a single page; typing a stop, service, or operator term narrows the current-page cards; changing page clears the filter; opening an evidence link and closing the route overlay keeps the results.

## 4. Scenario map

- Quickstart 1 pins User Story 1 (flat ranked pages, backend).
- Quickstart 3 pins User Stories 2–3 (cards, pager, filter, compact prose).
- Details: [data-model.md](./data-model.md), [contracts/answer-page.md](./contracts/answer-page.md).
