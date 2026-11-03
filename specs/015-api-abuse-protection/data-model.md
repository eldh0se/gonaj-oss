# Data Model: API Abuse Protection

No schema or migration. Both entities below are enforced in code against the existing throttle cache and request payloads.

## ThrottleBudget

A named per-endpoint, per-client allowance.

- **Fields**: `scope` (one of `journey_min`, `journey_day`, `transcribe_min`, `transcribe_day`), `rate` (DRF rate string, e.g. `"60/min"`), `window` (minute/day, implied by scope), `identity` (SHA-256 of client IP — raw IP never stored).
- **Relationships**: each scope counts independently; journey/transcribe scopes share nothing with the `transport_minute`/`transport_day` read scopes.
- **Validation rules** (from FR-001–FR-004, FR-007):
  - Rates come from env with safe compiled defaults; missing/empty env never yields an unbounded budget.
  - Only well-formed requests are counted; rejected (400) requests leave counters untouched.
  - Denial raises the standard throttled response with `Retry-After`; denial consumes no model quota.
- **State transitions**: none — fixed-window counters expire on their own; no manual reset path.

## RequestCaps

The size envelope for a single request.

- **Fields**: `max_question_chars` (500), `max_history_turns` (10), `max_turn_chars` (500 per turn), `max_context_bytes` (8192 serialized), `max_audio_bytes` (5MB, transcribe only), `audio_type` (WAV-only, transcribe only, unchanged).
- **Relationships**: caps apply to journey asks (all fields) and transcribe (audio fields only); caps are checked before budgets per FR-004/FR-005 ordering.
- **Validation rules** (from FR-005–FR-007):
  - Oversized requests are rejected with a plain-language size error before any model call and before budget accounting.
  - Every cap is env-overridable with the compiled default as fallback.
- **State transitions**: none — per-request checks, nothing stored.
