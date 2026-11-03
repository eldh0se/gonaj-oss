# Research: API Abuse Protection

## Decision 1: Reuse DRF SimpleRateThrottle + existing DB cache, no new deps

- **Decision**: New budgets are `SimpleRateThrottle` subclasses in `backend/apps/transport/api/throttling.py`, counting against the existing `transport_throttle_cache` database cache. No package, service, or schema change.
- **Rationale**: The repo already throttles reads this way (shared `transport_minute`/`transport_day`, hashed-IP keys, lazy rate lookup so settings/env overrides take effect); the threat model (single-client floods) fits fixed-window per-IP budgets. Reuse keeps constitution VI (simple synchronous stack).
- **Alternatives considered**:
  - Token bucket / sliding-window library — rejected: new dependency for precision the fixed windows already provide at this scale.
  - Reverse-proxy rate limiting (Caddy/Nginx) — rejected: budgets must key on the app's hashed-IP identity and share its test harness; proxy stays a dumb pipe (only trusted-header forwarding, already supported).

## Decision 2: Four independent scopes, detached from shared reads

- **Decision**: `journey_min` 60/min, `journey_day` 1500/day, `transcribe_min` 20/min, `transcribe_day` 300/day. Both views stop using `READ_THROTTLE_CLASSES`; the shared read budgets apply to map reads only. Clarify Q1 confirmed full independence (no shared backstop).
- **Rationale**: Per-endpoint ceilings bound the two LLM-costly paths separately; transcribe is tighter because audio ingress plus inference costs more per request than a text ask. Detachment guarantees a journey flood can never throttle innocent map readers (SC-001).
- **Alternatives considered**:
  - Keep shared budgets as a backstop — rejected in clarify Q1: contradicts SC-001/SC-002 and makes ceilings unpredictable.
  - Single combined journey+transcribe budget — rejected: text asks and audio uploads have very different unit costs; one ceiling would over-throttle one or under-protect the other.

## Decision 3: Validate shape/size before the budget check, explicitly in-view

- **Decision**: In `journey`/`transcribe`, parse + shape-check + size-cap the request first (400s), then run the budget check by driving the same throttle classes explicitly and raising DRF `Throttled` on denial (preserving the standard 429 + `Retry-After`). Rejected requests never reach the counter increment, so only well-formed requests consume budget. Clarify Q2 confirmed this order.
- **Rationale**: DRF's `@throttle_classes` decorator runs inside `initial()`, before the view body — with decorators, an oversized request would burn a budget slot (or get a 429 instead of its precise size error). Explicit ordering makes the 400-before-429 contract obvious and unit-testable per view. Raising `Throttled` keeps the exact 429 wire behavior clients already handle.
- **Alternatives considered**:
  - Keep decorators, accept throttle-first — rejected in clarify Q2: violates FR-004/FR-005 ordering and burns budget on garbage.
  - Convert views to class-based with `initial()` override — rejected: larger refactor of working function views for the same ordering an explicit call achieves.
  - Return 400 from inside a throttle class — rejected: throttles only vote allow/deny; error shaping belongs in the view.

## Decision 4: Env-tunable budgets/caps with safe compiled defaults

- **Decision**: Settings follow the existing `env()` pattern: `JOURNEY_THROTTLE_MINUTE` ("60/min"), `JOURNEY_THROTTLE_DAY` ("1500/day"), `TRANSCRIBE_THROTTLE_MINUTE` ("20/min"), `TRANSCRIBE_THROTTLE_DAY` ("300/day"), `JOURNEY_MAX_QUESTION_CHARS` (500), `JOURNEY_MAX_HISTORY_TURNS` (10), `JOURNEY_MAX_TURN_CHARS` (500), `JOURNEY_MAX_CONTEXT_BYTES` (8192). Missing/empty values fall back to the compiled defaults; the service never starts unbounded. Clarify Q3 confirmed the numbers.
- **Rationale**: Rates are deployment knowledge (quota, traffic), not code; env keeps production tuning a config change. DRF rate strings keep the format operators already know from `transport_minute`.
- **Alternatives considered**:
  - Hard-code budgets — rejected: violates FR-007, forces deploys for tuning.
  - Django settings module per environment — rejected: heavier than env vars, against the repo's existing `env()` convention.

## Decision 5: Extend existing throttle + journey tests, keep clamp coverage

- **Decision**: Extend `backend/apps/transport/tests/test_read_throttle.py` with independence cases (flood journey → reads/transcribe unaffected and vice versa) and `backend/apps/journey/tests/` with order cases (oversized + over-budget → 400; rejected requests leave budget counters untouched; throttled → 429 + `Retry-After` with no model call). Existing page/page_size clamp coverage stays green and untouched.
- **Rationale**: The suites that own throttling and journey behavior pin the new contract; failing-first per repo norm. Clamp behavior is adjacent view logic that must not regress.
- **Alternatives considered**: New test module — rejected; the existing files own this behavior.

## Decision 6: Document DEBUG, ALLOWED_HOSTS, and proxy env for production

- **Decision**: Deployment docs gain a short production-hardening section: `DEBUG` off, `ALLOWED_HOSTS` set, `TRANSPORT_TRUSTED_PROXY` set only to the known proxy address (it switches throttle identity to the forwarded client), plus the new budget/cap env vars with defaults. No code behavior change beyond the budgets themselves.
- **Rationale**: Per-IP throttling behind a proxy is only correct when the proxy header is trusted explicitly; misconfiguring it (trust-any) lets clients spoof identity. Documenting it with the budgets keeps the whole production story in one place.
- **Alternatives considered**: Auto-trusting forwarded headers — rejected: lets any client claim any IP, defeating per-IP budgets (privacy + security).
