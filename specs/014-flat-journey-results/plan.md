# Implementation Plan: Flat Paginated Journey Results

**Branch**: `014-flat-journey-results` | **Date**: 2026-11-03 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/014-flat-journey-results/spec.md` plus the requester's technical direction (Django + DRF with SQLite-portable Python ranking plus React cards; flatten `_rank_pairs` in `agent.py`; `page`/`page_size` on `POST /journey/` default 5 max 20; page-scoped prose; drop `option_groups`; cards with boarding/alighting/walk notes and evidence in `JourneyPanel.jsx` + `journey.js`).

## Summary

Replace the per-operator `option_groups` answer with one flat relevance-ranked `options` array plus `page` pagination (`page`/`page_size` request, `total_options`/`total_pages` response). Ranking stays the existing pure-Python `(stop_count, route_id)` order applied globally instead of per group; each option carries its `operator` (and route `network`) as display data. The prose answer becomes a page-scoped summary capped at 1000 characters. The frontend renders option cards with a Prev/Next pager matching the routes/stops tabs (fetch the requested page) and a client-side text filter over the current page (changing page clears the filter). See [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md).

## Technical Context

**Language/Version**: Python 3.13, Django + Django REST Framework (per `backend/requirements.txt`); React + JSX frontend (existing scaffold precedent)

**Primary Dependencies**: No new dependencies — pure-Python `sorted` ranking (SQLite-portable, no DB-specific SQL), existing DRF pagination-style params, existing `fetch` client

**Storage**: No schema change; options are computed per request from verified pairs, never stored

**Testing**: Django test runner — update `test_ranked.py` (flat shape) and `tests/test_area_search.py` (area-to-area paging); frontend `vitest` for cards, pager, filter, overlay-retain, and disclaimer

**Target Platform**: Linux server; single deployable app (web + PostgreSQL)

**Project Type**: web-service (monorepo; backend ranking/paging plus additive frontend cards in the existing journey panel)

**Performance Goals**: Page fetch stays within the existing journey-answer latency budget (single model turn + one bounded re-rank); pages are small (≤20 options) so render cost is trivial

**Constraints**: Read-only product (no dataset writes); plain-language errors only; `page` starts at 1, `page_size` default 5 max 20 (larger clamped, never an error); prose ≤1000 chars; filter is client-side over loaded pages only; no server-side operator filter; no `bbox` ends; no token-weighted relevance tuning

**Scale/Scope**: One answer shape plus one panel UI; option volume bounded by the existing 200-pair verifier cap, served 20 per page max

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. MVP validation first** — PASS: directly answers "how do I get from A to B" for area-to-area queries with many options.
- **II. Read-only product** — PASS: ranking/paging compute over verified pairs; no dataset mutation, no new feedback mechanics.
- **III. Open access / minimal data** — PASS: no accounts, no tracking; filter state stays in the client.
- **IV. Monorepo separation** — PASS: `backend/` answer shape plus `frontend/` cards; cross-boundary traffic stays on the versioned REST API (`POST /api/v1/journey/` with additive `page`/`page_size`).
- **V. App-owned data + provenance** — PASS: reads existing stops/routes only; provenance untouched.
- **VI. Simple synchronous stack** — PASS: plain Python `sorted` (SQLite-portable, no engine-specific SQL), no queue/service/worker; no transcode equivalent — pure data reshaping.
- **VII. Admin as data interface** — N/A: no data-management change.
- **VIII. Schedule gating** — PASS: no times, durations, or frequencies involved.
- **IX. Meta AI integration** — PASS: no model change; answers stay evidence-grounded with refuse-on-unknown; model/provider/latency meta unchanged; voice input unaffected.

*Re-check after Phase 1 design (2026-11-03): still PASS on all gates. No new dependency, service, migration, tracking, or privacy change; the answer contract gains additive paging fields and drops `option_groups` (prose summary is the compat path).*

## Project Structure

### Documentation (this feature)

```text
specs/014-flat-journey-results/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── answer-page.md   # flat paged answer contract (public contract delta vs 004/010)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── apps/
│   └── journey/
│       ├── agent.py     # flatten _rank_pairs to options (operator+network), global (stop_count, route_id) order, page slice, page-scoped prose ≤1000 chars, drop option_groups
│       ├── views.py     # journey: accept page/page_size (default 5, max 20, clamp), pass through
│       └── tests/       # test_ranked.py (flat shape), test_area_search.py (paging)
└── requirements.txt     # unchanged (no new deps)

frontend/
└── src/
    ├── api/journey.js                  # postJourney passes page/page_size
    └── components/JourneyPanel.jsx     # option cards (route, boarding/alighting, walk notes, evidence), shared Prev/Next pager, client-side filter
```

**Structure Decision**: Backend ranking/paging plus additive frontend cards in the existing journey panel. The public answer contract changes (flat `options` + pagination replace `option_groups`); prose summary is the old-renderer compat path.

## Complexity Tracking

> No constitution violations — table intentionally empty.
