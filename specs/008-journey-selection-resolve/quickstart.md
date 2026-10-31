# Quickstart: Journey Selection Resolve

**Feature**: [spec.md](spec.md) | **Contracts**: [contracts/selection.md](contracts/selection.md), base [004 journey.md](../../004-journey-agent/contracts/journey.md) | **Data model**: [data-model.md](data-model.md)

Validates the fix end to end: a valid pick advances to a verified answer or honest refusal and is never re-prompted; both-ends flow retains the first pick; invalid picks refuse safely.

## Prerequisites

- Backend deps installed (`backend/requirements.txt`), Postgres available for dev; tests run SQLite-portable.
- Frontend deps installed (`frontend/package.json`).
- No model key needed for selection tests (stubbed model client; fast-path makes no model call).

## Run the gates

```bash
# backend — 125 tests including new SelectionTests
python backend/manage.py test apps.journey apps.transport tests
```

```bash
# frontend — 53 tests including payload test
npm test -- --run
```

Expected: both suites green. Selection fast-path tests assert zero model calls on the valid-pick path.

## Manual validation (dev servers running)

1. Ask an ambiguous journey: `POST /api/v1/journey/` with `{"question": "How do I get from North to South?"}` → expect `status: disambiguate` with `candidates` (each with `detail`), `slot`, and `offered_ids`.
2. Pick one by click: resend with `question` = candidate name, `history` = original question, and `context` = `{candidate_stop_ids, selected_stop_id, slot, resolved}` → expect `status: ok` with evidence-linked routes and `/routes/:id` links, or `status: refuse` with a no-direct-service message. Never the identical candidate prompt.
2b. Pick one by typing: resend with `question` = exact candidate name (or `1` / `first`) and the previous `context` minus `selected_stop_id` → expect the same outcome as the click path (server derives the pick by unambiguous text match).
3. Both ends ambiguous: pick the first end → expect a prompt for the remaining end only (first pick retained). Pick the second → expect verified answer or honest refusal.
4. Forged pick: send `selected_stop_id` not in `candidate_stop_ids` → expect safe `refuse`, no invented stops/routes.
5. Missing `resolved`: omit `resolved` while `slot` requires it → expect safe `refuse`.
6. New question mid-prompt: ask an unrelated journey → expect a fresh answer flow; stale candidates do not leak.

## What good looks like

- Every cited route links to `/routes/:id` evidence; answers contain no times and no transfers.
- Selection responses carry `meta: {model: none, provider: local-fallback, resolution: selection}` (outage fallback carries no `resolution` key).
- Candidate lists show distinguishing `detail` after each name.
- Logs carry model/provider/latency/tools_used only — no questions, answers, transcripts, or PII.
