# Quickstart: Validating Debug and Production Logging

**Feature**: `007-debug-production-logging` | **Date**: 2026-10-31

Validates the spec end to end without reading implementation
code. Each scenario maps to its spec story and success
criterion; see [contracts/logging.md](contracts/logging.md)
for the entry format under test.

## Prerequisites

- Backend virtualenv with dev requirements installed;
  database reachable (`compose.yml` or local Postgres).
- Required env vars set (`DJANGO_SECRET_KEY`, plus Postgres
  vars as in `backend/config/settings.py`).
- Frontend: `npm install` under `frontend/` (Vitest suite).

## Scenario 1 — Debug mode is verbose (Story 1, SC-001)

1. Start the backend with `DJANGO_DEBUG=1`.
2. Exercise a failing path (e.g. request an unknown route id)
   and a successful search.
3. Confirm the captured output shows `DEBUG`-level entries
   tracing the request steps, and the failure entry names
   the component and operation (method + path).

Expected: a developer unfamiliar with the code can name the
failing component and operation from the log lines alone.

## Scenario 2 — Production mode stays quiet but errors surface (Story 2, SC-002, SC-003)

1. Restart the backend with `DJANGO_DEBUG=0` (and
   `DJANGO_ALLOWED_HOSTS` permitting localhost).
2. Exercise representative normal traffic (route list,
   stop search, connectivity check).
3. Confirm: no `DEBUG` entries appear in the output.
4. Trigger a server-side failure (e.g. journey endpoint with
   the model backend unreachable).
5. Confirm: an `ERROR` entry with timestamp, operation
   context, and traceback is recorded; the API response
   itself keeps its plain-language shape with no internals.

## Scenario 3 — Import command logs its outcome (Stories 1–2)

1. Run the snapshot import command against a fixture
   snapshot in both modes.
2. Confirm an `INFO` outcome entry (snapshot label, counts)
   on success and an `ERROR` entry naming the fatal anomaly
   on failure, in both modes.

## Scenario 4 — No secrets or private content in logs (Story 3, SC-004)

1. With each mode running, exercise authenticated-adjacent
   paths: configuration load, journey ask, voice
   transcription, feedback submission.
2. Sweep the captured output for secret values, tokens,
   question/answer text, and transcripts.
3. Confirm zero occurrences.

## Scenario 5 — Frontend console is dev-only

1. Run `npm run dev`, trigger an API failure, confirm a
   concise debug line in the browser console.
2. Run `npm run build` and confirm the debug helper is
   eliminated from the production bundle (no console output
   on the same failure; the UI error renders as before).

## Automated checks

- Backend: Django test suite covering mode-dependent
  thresholds (`assertLogs`), error-boundary entries, and
  the redaction rule.
- Frontend: Vitest suite asserting the debug helper is
  silent when `import.meta.env.DEV` is false.

Passing means all five scenarios behave as above and both
suites are green.
