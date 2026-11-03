# Contract: Throttle Budgets and Request Caps

## Scopes and rates (defaults; all env-overridable)

| Scope | Endpoint | Default | Env var |
|-------|----------|---------|---------|
| `journey_min` | `POST /api/v1/journey/` | 60/min per client IP | `JOURNEY_THROTTLE_MINUTE` |
| `journey_day` | `POST /api/v1/journey/` | 1500/day per client IP | `JOURNEY_THROTTLE_DAY` |
| `transcribe_min` | `POST /api/v1/journey/transcribe/` | 20/min per client IP | `TRANSCRIBE_THROTTLE_MINUTE` |
| `transcribe_day` | `POST /api/v1/journey/transcribe/` | 300/day per client IP | `TRANSCRIBE_THROTTLE_DAY` |

Journey/transcribe calls do not count toward `transport_minute`/`transport_day`, and map reads do not count toward the new scopes. Client identity is the SHA-256-hashed IP (existing scheme); behind a proxy, the forwarded address is used only when `TRANSPORT_TRUSTED_PROXY` names the proxy.

## Size caps (defaults; all env-overridable)

| Cap | Default | Env var | Applies to |
|-----|---------|---------|------------|
| Question text | 500 chars | `JOURNEY_MAX_QUESTION_CHARS` | journey |
| History | 10 turns | `JOURNEY_MAX_HISTORY_TURNS` | journey |
| History turn | 500 chars each | `JOURNEY_MAX_TURN_CHARS` | journey |
| Context | 8KB serialized | `JOURNEY_MAX_CONTEXT_BYTES` | journey |
| Audio | 5MB, WAV-only | unchanged (`MAX_AUDIO_BYTES`) | transcribe |

## Rejection shapes (unchanged success payloads)

- **Oversized/malformed** → `400` with the existing plain-language JSON error style. Checked before the budget check, so an oversized request gets the size error even when the client is over budget, and consumes no budget.
- **Over budget** → `429` with a `Retry-After` hint (seconds) and a plain-language retry message. No model or transcription work runs.
- Only well-formed requests (passed shape + size checks) count toward the minute/day counters.

## Production env (see also deployment docs)

- `DEBUG` off; `ALLOWED_HOSTS` set to the serving domain(s).
- `TRANSPORT_TRUSTED_PROXY` set to the known proxy address only — never wildcard — so per-IP identity is trustworthy.
- Budget/cap env vars above; unset/empty values fall back to the compiled defaults.
