# Quickstart: Validate Agent-Based Area Search

Proves feature 012 end to end. Run from `backend/` with the Django test
runner (no network, no model key — the suite stubs the provider and runs the
tools for real against factory data, per existing journey-test convention):

```bash
cd backend
python manage.py test apps.journey -v 2
```

Prerequisites: working Django test setup (Postgres per `config/settings.py`
for integration runs; journey unit tests use factories + stubbed
`apps.journey.providers.meta`, following `test_journey.py`).

## Validation scenarios

Build fixtures with `apps.transport.tests.factories`: an origin cluster
(e.g. two `Aluva` stops opposite sides + one walkable mate), a destination
with a near group `{K1, K2, K3}` (K1/K2 opposite sides ≤150m, K3 within
150m of the served stop) and a far group `{K4, K5}` (>150m away), plus one
servable route through origin member → K1 with `pos_from < pos_to`.

| # | Scenario | Run | Expected |
|---|----------|-----|----------|
| 1 | Area→area happy path | `run_journey("Aluva to Kaloor")`, stubbed model calling `search_places` → `find_routes_matrix` → `get_route_detail` | Answer names exact stops + `/routes/:id` + walk note (`K2 (20m walk)` style); no pick prompt |
| 2 | Wrong side | Same as 1 where the named side is unserved but the opposite mate is | Same answer shape as 1; never an exact-id refusal |
| 3 | Ambiguous origin | Mirror of 1 with duplicated origin name | Same exact-plus-walk-note shape on the boarding end |
| 4 | No viable pair, place matched | Route serves only the reverse direction | Polite no-direct refusal; no pick prompt |
| 5 | Cap truncation | >200 pairs with the only viable pair ranked last | Map/list pick (pairs went untested), not refusal |
| 6 | Unknown place | `search_places(query="Zzxq")` → `empty` | Map/list pick for re-resolution, not refusal |
| 7 | Over-wide map area | `search_places(bbox=<huge>)` → `zoom_in` | Narrow-the-area request; no silent substitution |
| 8 | No bypass | Full selection context with wrong-side `selected_stop_id` | Matrix flow answers (scenario 2 shape); `answer_direct` never answers from the raw pair |
| 9 | Single-ended query | `"Kaloor buses?"` (no origin) | Legacy behavior preserved (out of scope) |
| 10 | New tools | `distance_m` known pair; `nearby_stops` radius 500/over-2000/invalid | Correct meters; ordered ≤100 stops; error on over-max/invalid |
| 11 | Audit | Any tool-calling run | Log line lists `search_places,find_routes_matrix,...` in `tools_used` (007, via `execute_tool`) |
| 12 | Forbidden content | Draft containing a time/duration/transfer | Verifier rejects; one repair retry; then refuse |

Scenarios 4–7 pin clarify outcome C; 8 pins FR-011; 10 pins FR-003/FR-009
contracts; 11 pins the 007 audit path. Details (factory layouts, stubbed
tool-call scripts, overflow and rounding cases) belong in `tasks.md` and
the implementation phase — this file stays a validation guide.
