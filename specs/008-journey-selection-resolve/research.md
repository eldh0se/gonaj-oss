# Research: Journey Selection Resolve

**Feature**: [spec.md](spec.md) | **Date**: 2026-10-31 | **Branch**: `008-journey-selection-resolve`

No NEEDS CLARIFICATION remained: the requester fixed stack (Django 5.2 + DRF, OpenAI SDK server-side for `muse-spark-1.3` — code default `JOURNEY_MODEL`; the request input spelling `muse-spark-1.3-contributor` is aligned to the code/004-contract value here, env governs at runtime; React Vite frontend, Postgres with SQLite-portable tests, existing 003 plus 006 queryset helpers) and the exact behaviour (fast-path selection, validation, both-ends context, additive contract, frontend payload fix, test list). Each decision below records what was chosen, why, and what was set aside.

## Decision: Local selection fast-path at top of `run_journey`, never calls model

- **Decision**: Add `_resolve_selection(context)` in `backend/apps/journey/agent.py` returning `(from_id, to_id)` or `None`. At the top of `run_journey` (after blank-question guard, before any `provider.complete_with_tools` call), when it returns a valid pair, call `tools.find_routes` directly, `_verify_route` each returned route for travelling order, return `_answer_payload` on the first verified route or a `refuse` with `_NO_DIRECT` when empty. Set `meta` to `model: none`, `provider: local-fallback` on this path, keep `tools_used` audit accurate (records the direct `find_routes` call).
- **Rationale**: The reported defect is an indefinite repeat prompt after a valid pick; routing the pick through the model re-invites hallucination and repeat prompts. A deterministic DB-backed path guarantees SC-001 (valid pick advances to verified answer or honest refusal, never a repeated prompt) and keeps latency to DB lookups only.
- **Alternatives considered**: Letting the model resolve the pick via the existing follow-up system hint (rejected — current behaviour proves it loops; model remains the eloquence layer, never the source of truth for IDs); handling selection in `views.py` (rejected — contract requires `views.py` pass-through verification only; agent owns resolution and verification).

## Decision: Strict `_resolve_selection` validation, invalid picks refuse safely

- **Decision**: Validate `selected_stop_id` is `int` (excluding `bool`) and a member of `candidate_stop_ids`; `slot` in `{"from", "to"}`; `resolved` is a dict with integer `id`. Any violation returns `None` (falls through to existing model/refusal handling), and forged IDs or missing `resolved` produce a safe refusal, never an invented stop or journey. Same-road opposite-side duplicates are ordinary distinct candidates — no extra confirmation loop.
- **Rationale**: Satisfies FR-002/FR-005 and SC-003; membership check is the forgery guard; `bool` exclusion closes the `True == 1` Python pitfall in the existing `_validate_tool_args` style.
- **Alternatives considered**: Coercing string IDs to int (rejected — masks forgery and modality bugs; frontend must send real IDs); fuzzy-matching the pick question text against candidates (rejected — pick identity comes from IDs, question text is display only).

## Decision: Extend disambiguation context to both-ends-ambiguous slots

- **Decision**: Keep the existing disambiguation helper shape but extend it for the no-singleton case: instead of returning `(None, None)`, return `slots: {from_ids, to_ids}` plus `surviving_context: {other_end_ids}` so the first valid pick is retained and only the still-unresolved end is re-prompted. Single-end ambiguity keeps the current single-list shape.
- **Rationale**: Directly implements FR-003 and SC-002 (two valid picks complete a both-ends-ambiguous journey; resolved ends are never re-prompted identically). The surviving-context field is what lets a stateless per-request server carry the first pick forward without session storage.
- **Alternatives considered**: Server-side session store for pending picks (rejected — violates the stateless-per-request design and Principle III minimal-data posture); resolving both ends in one turn (rejected — passenger picks one end at a time; forcing both complicates the UI and the contract).

## Decision: Distinct `none` / `local-fallback` meta on the selection path

- **Decision**: Selection fast-path meta is `model: none`, `provider: local-fallback`, distinguishable from model-outage fallback if operators need it. Log line keeps `model, provider, latency_ms, tools_used` shape; no question/answer/transcript/PII in logs.
- **Rationale**: Operators must tell "answered locally from a passenger pick" apart from "model failed, fell back". Reuses the existing `_meta(latency, fallback=True)` shape and the existing journey log format, satisfying Principle IX meta-in-response-and-logs.
- **Alternatives considered**: Reusing the model ID in meta on the selection path (rejected — would falsely attribute a deterministic DB answer to the model); adding new log fields with payload content (rejected — PII/minimisation violation).

## Decision: Additive-only contract change, `views.py` unchanged except pass-through

- **Decision**: Amend `specs/004-journey-agent/contracts/journey.md` additively only: `disambiguate` gains `{slot, resolved: {id, name}, offered_ids}`; selection reply carries `{question, history[original], context{candidate_stop_ids, selected_stop_id, slot, resolved}}`. No new endpoints, no shape removals, no `views.py` logic change beyond the existing pass-through verification.
- **Rationale**: Existing clients and tests keep passing; additive fields are the smallest change that carries slot identity and surviving context through the stateless boundary.
- **Alternatives considered**: New `/journey/resolve` endpoint (rejected — new handler surface, breaks "no new handlers" scope; stateless context already solves it); breaking change to `disambiguate` shape (rejected — would invalidate 004 contract tests).

## Decision: Frontend `choose` sends full selection context, `ask` preserves history

- **Decision**: `frontend/src/components/JourneyPanel.jsx`: `choose(candidate, payload)` sends the full payload plus `candidate_stop_ids`, `selected_stop_id`, `slot`, and `resolved`; `ask()` stops forcing `history: []` and preserves the original question. Render path unchanged.
- **Rationale**: The backend fast-path keys entirely off IDs/slot/resolved; dropping any field forces the model-loop fallback and reproduces the bug. Preserving history (instead of resetting it) keeps the original question available for the second-end prompt. No render change keeps AI-unverified labelling and evidence-link behaviour intact.
- **Alternatives considered**: Sending only `selected_stop_id` (rejected — backend cannot validate membership or slot without the candidate list); resetting history on each pick (rejected — loses the original question the second-end prompt needs).

## Decision: Read-only MCP-compatible tools, no new handlers or packages

- **Decision**: No new Python or npm packages, no new endpoints/handlers, no migrations. Tools stay the existing three read-only functions over canonical tables via shared 003 helpers plus 006 annotations; schemas stay MCP-compatible with no MCP server stood up. Postgres prod with SQLite-portable test SQL (no Postgres-only constructs).
- **Rationale**: Constitution Principles VI (simple synchronous stack), IX (read-only MCP-compatible tools, no MCP server), and V (canonical dataset) all require it; keeps the change reviewable as a ~100-line agent diff plus a ~10-line frontend diff.
- **Alternatives considered**: New resolve tool or endpoint (rejected — scope explicitly forbids new handlers); Postgres-specific SQL in selection path (rejected — breaks the SQLite-portable test gate).

## Decision: Test strategy — SelectionTests plus frontend payload test plus full regression

- **Decision**: Backend `SelectionTests`: duplicate-fixture both-ends-ambiguous flow (pick first end → prompt for remaining end only; pick second → verified answer or honest refusal), forged-ID refusal, missing-`resolved` refusal. Frontend: payload test asserting IDs plus slot plus surviving context are sent and history preserves the original question. Regression gates: `manage.py test apps.journey apps.transport tests` 125 OK, `npm test -- --run` 53 passed.
- **Rationale**: Mirrors the defect (both-ends ambiguous + invalid picks) with deterministic stubbed-model tests; full-suite gates catch contract or render regressions.
- **Alternatives considered**: Model-backed integration tests (rejected — network/key dependence, flaky); snapshot-only frontend tests (rejected — would not assert the ID/slot/context payload the backend depends on).

## Addendum: Post-Analyze Resolutions (2026-10-31)

Addresses the HIGH and MEDIUM findings from `/speckit-analyze`.

### Resolution: Selection meta carries `resolution: "selection"` (was: identical to outage fallback)

- **Decision**: The selection fast-path sets `meta` to `model:none / provider:local-fallback / resolution:selection`; the existing model-outage `fallback()` shape is untouched (no `resolution` key). Operators distinguish by key presence; `tools_used` (direct `find_routes` entry via manual tracker bookkeeping) corroborates.
- **Rationale**: The plan's "distinct" claim was false for identical `model`/`provider` values. An additive optional key fixes the claim without breaking existing assertions on the shared shape.
- **Alternatives considered**: Separate provider string for selections (rejected — invents a fake provider); relying on latency/`tools_used` alone (rejected — implicit, log-scraping instead of a contract field).

### Resolution: Typed replies derive `selected_stop_id` by unambiguous text match

- **Decision**: `_resolve_selection(context, question_text)` gains a typed path: when `selected_stop_id` is absent, match normalized `question_text` against the offered candidates in order — case-insensitive exact name matching exactly one candidate, or a 1-based position / ordinal (`1`, `first`, `second`, …) matching exactly one slot entry. Zero or multiple matches → `None` (safe refusal, same as forged IDs).
- **Rationale**: Spec FR-001/Edge Cases accept picks "by position, exact name, or visible choice"; the click-only fast-path left typed replies to fall through to the model loop that caused the original defect.
- **Alternatives considered**: Frontend-side text→ID matching (rejected — duplicates matching logic across the REST boundary; server owns resolution); model-loop handling of typed picks (rejected — reproduces the repeat-prompt failure mode).

### Resolution: `tools_used` audit via manual tracker bookkeeping

- **Decision**: The fast-path appends `tracker["tools_used"].append("find_routes")` plus matching `calls`/`findings` entries, mirroring the `execute_tool` shape, since the direct `tools.find_routes` call bypasses `execute_tool`.
- **Rationale**: Keeps the operator log accurate without routing a deterministic lookup through the model-tool validation path.

### Resolution: Every `disambiguate` carries slot identity; helper is new, not extended

- **Decision**: The disambiguation helper is created (no `_disambiguation_context` exists in code) and emits `slot`/`offered_ids`/`resolved` plus per-candidate `detail` on every prompt; both-ends adds `slots`/`surviving_context`.
- **Rationale**: Single-end enrichment had no explicit build task; naming it "extend" would send implementers searching for a nonexistent function.

### Resolution: Candidate `detail` from `name_ml`, else rounded coordinates

- **Decision**: `detail` is `Stop.name_ml` when present, else `lat,lon` rounded to 4 decimals; optional and additive; frontend renders it after the name when present.
- **Rationale**: Satisfies the spec's "name plus distinguishing detail" rule using only existing `Stop` fields — no new queries, no locality data that does not exist.
- **Alternatives considered**: Coordinates-only always (rejected — less human-readable where `name_ml` exists); new locality annotation query (rejected — scope creep, extra subqueries).
