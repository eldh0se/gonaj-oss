# Quickstart: API Abuse Protection

Proves per-endpoint budgets, fail-fast size caps, and env tunability. Run from the repo root against a dev server with a test database.

## 1. Independent journey budget (needs backend)

Drive `POST /api/v1/journey/` from one client past 60 requests in a minute (lower `JOURNEY_THROTTLE_MINUTE` for a faster check, e.g. `5/min`).

- Expected: the 61st (or 6th) request returns `429` with a `Retry-After` header and a plain-language retry message; no model work runs for it.
- From a second client IP in the same window: asks succeed, `GET /api/v1/stops/` reads succeed, and transcribe uploads succeed — budgets are per client and per endpoint.

## 2. Independent transcribe budget (needs backend)

Drive `POST /api/v1/journey/transcribe/` with small valid WAVs past its per-minute budget (lower `TRANSCRIBE_THROTTLE_MINUTE` for a faster check).

- Expected: further uploads return `429` + `Retry-After`; journey asks from any client still succeed.

## 3. Size caps fail fast (needs backend)

POST journey asks with (a) a >500-char question, (b) an 11-turn history, (c) an over-8KB context object, each from a fresh client.

- Expected: each returns `400` with a plain-language size error; repeating the same oversized request never triggers `429` (rejections consume no budget); no model call runs.

## 4. Scenario map

- Quickstart 1 pins User Stories 1 (journey budget) and the independence half of SC-001.
- Quickstart 2 pins User Story 2 (transcribe budget) and SC-002.
- Quickstart 3 pins User Story 3 (caps) and SC-003.
- SC-004 (env-only retune): re-run step 1 with a raised `JOURNEY_THROTTLE_MINUTE` and confirm the new ceiling applies with no code change.

Details: [contracts/throttle-budgets.md](./contracts/throttle-budgets.md), [data-model.md](./data-model.md).
