# Data Model: Flat Paginated Journey Results

**Feature**: [spec.md](./spec.md) | **Date**: 2026-11-03

No migrations: no schema change. All entities below are transient
(in-request response shapes) computed from verified route pairs.

## JourneyOption (one flat result)

Per direct service, in global relevance order (`stop_count` ascending,
then route id ascending):

- `route`: `{id, name, evidence}` — evidence is a frontend `/routes/:id` address (unchanged).
- `boarding_stop` / `alighting_stop`: `{id, name}` of the resolved stops for this option.
- `operator`: display string for the card; `"Other services"` when the route has none.
- `network`: route network string as stored (may be empty); display-only, never filtered server-side.
- `stop_count`: number of stops on the route (the rank key; smaller = more direct).
- `boarding_hint`: e.g. "Board at Kaloor (Kaloor Bus Stand)" (unchanged).
- `also_nearby_boarding` / `also_nearby`: member-stop names folded into this option (unchanged).
- `overflow_nearby_boarding` / `overflow_nearby`: counts of further member stops (unchanged).
- Walk notes: derived boarding/alighting proximity notes (unchanged content, rendered on the card).

Lifecycle: built per request from `_rank_pairs` output, sliced to the requested page, never stored.

## PagedAnswer (page slice)

Ranked successful answers carry, alongside the unchanged `status: "ok"`, `answer` prose, `destinations`, and `meta`:

- `options`: `JourneyOption[]` for the requested page only (may be empty past the last page).
- `page`: 1-based page number served (echoes the request, default 1).
- `page_size`: options per page served (request value clamped to max 20, default 5).
- `total_options`: total flat options across all pages.
- `total_pages`: `ceil(total_options / page_size)` (0 options → 0 pages).

Removed: `option_groups` no longer appears on any answer.

## Validation rules

- `page < 1` → treated as 1; `page_size < 1` → default 5; `page_size > 20` → clamped to 20. Never an error.
- Page past the last → `options: []` with unchanged `total_options`/`total_pages`.
- Prose `answer` summarizes the current page (count + top option), at most 1000 characters.
- Disambiguate / refuse / fallback shapes carry no `options` and no paging fields (unchanged).
