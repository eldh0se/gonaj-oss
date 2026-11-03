# Research: Flat Paginated Journey Results

**Feature**: [spec.md](./spec.md) | **Date**: 2026-11-03

Phase 0 output. The requester's technical direction resolved the unknowns, so this records the decisions with rationale and rejected alternatives. No external research was needed: every choice reuses existing in-repo mechanisms.

## Decision 1: Flatten in `agent.py`, keep the existing order key

- **Decision**: `_rank_pairs` keeps building per-option dicts but returns one flat list ordered globally by `(stop_count, route["id"])` — the same key it already uses inside each group — instead of operator groups. Each option gains `operator` (with `"Other services"` fallback preserved) and route `network` as display fields.
- **Rationale**: SQLite-portable (pure-Python `sorted`, no engine-specific SQL) and zero ranking-behavior change: the global order is exactly what the groups already produced within themselves, so relevance is preserved while the group-hiding defect disappears.
- **Alternatives considered**:
  - Re-rank with token-weighted scoring: rejected — explicitly out of scope.
  - DB-level `ORDER BY` with window functions: rejected — engine-specific SQL for no benefit; the pair volume is already capped at 200 by the verifier.

## Decision 2: Page params on `POST /journey/`, default 5 max 20

- **Decision**: The journey request accepts `page` (1-based, default 1) and `page_size` (default 5, max 20, larger values clamped, never an error). The answer carries `options` (this page), `total_options`, `total_pages`, `page`, `page_size`.
- **Rationale**: Additive, backward-compatible params on the existing endpoint; small pages keep render cost trivial and match the card UI (5 cards fill a panel without scrolling fatigue). Page beyond last returns empty `options` with the same totals.
- **Alternatives considered**:
  - Cursor/opaque tokens: rejected — overkill for a ≤200-item recomputed list; page numbers are debuggable and testable.
  - Server-driven infinite scroll (no page concept): rejected — the spec requires an explicit pager control with a defined end.

## Decision 3: Page-scoped prose capped at 1000 chars, drop `option_groups`

- **Decision**: `rank_pairs` prose becomes a summary of the current page (count + top option, e.g. "24 direct options; quickest: ..."), hard-capped at 1000 characters; `option_groups` is removed from the answer. `destinations` (up to 5) is unchanged.
- **Rationale**: Fixes the unbounded-prose overflow; the cap (clarified 2026-11-03) makes SC-004 mechanically testable. Prose stays the old-renderer compat path since the frontend ignores `option_groups` anyway.
- **Alternatives considered**:
  - Keep `option_groups` alongside flat options: rejected — dual shapes reintroduce the grouping defect and double the payload.
  - Prose enumerating only the current page without a cap: rejected — still unbounded in the pathological case the cap guards.

## Decision 4: React cards + shared Prev/Next pager + client-side filter

- **Decision**: `JourneyPanel.jsx` renders one card per option (route name, boarding/alighting stops, boarding hint, walk notes, evidence link, operator). Paging reuses the shared `Pager` from `ResultsList.jsx` (Prev/Next + "Page X of Y · N options", hidden on a single page) so journey results paginate exactly like the routes/stops tabs; each page is fetched from the server and replaces the cards. Evidence links use client-side `Link to` navigation so opening a route and closing its overlay keeps the journey results. The text filter narrows rendered cards by stop, service, and operator text on the current page only; changing page clears it.
- **Rationale**: No new dependency; matches the existing panel patterns (shared pager, `--gonaj-*` tokens, no new visual identity). Client-side filtering avoids extra round trips and keeps filter state out of the server (constitution III). Client-side evidence navigation avoids a full-page reload that would wipe search state.
- **Alternatives considered**:
  - Server-side filter/search param: rejected — spec puts the filter on the current page; a server filter would also need operator-filter semantics, explicitly out of scope.
  - Bespoke Load more accumulation: rejected — diverges from the routes/stops tab pager the frontend already uses; per-page server fetch keeps memory bounded and matches the tab UX.

## Decision 5: Test updates over new harness

- **Decision**: Update `test_ranked.py` to the flat shape (order, operator/network carried, prose cap, no groups) and extend `tests/test_area_search.py` with paging cases (page slices, totals, clamp, beyond-last, exact-multiple). Frontend `vitest` covers cards, pager navigation, filter/clear, overlay-retain, and the agent-mistakes disclaimer.
- **Rationale**: Reuses the two suites that already pin ranking and area search; failing-first per repo norm.
- **Alternatives considered**: New test module — rejected; the existing files own this behavior.
