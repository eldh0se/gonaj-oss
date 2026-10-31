# Data Model: Debug and Production Logging

**Feature**: `007-debug-production-logging` | **Date**: 2026-10-31

This feature creates **no persistent entities** — no models,
no migrations, no schema change. The structures below are
runtime-only (log records, configuration, redaction rules)
documented here so implementers and reviewers share one
vocabulary. See [contracts/logging.md](contracts/logging.md)
for the operator-facing field contract.

## Runtime structures (not stored)

### Log Entry

A single emitted record. Fields:

| Field | Meaning | Required |
|---|---|---|
| `timestamp` | Unambiguous time of the event, timezone-aware | Always |
| `level` | Severity: `DEBUG`, `INFO`, `WARNING`, `ERROR` | Always |
| `component` | Logger/module name identifying the area (e.g. transport API, journey agent, importer) | Always |
| `message` | One-line human-readable description of the event | Always |
| `operation` | What was being done when the event occurred (request method + path, command name + snapshot label, model call) | On warnings and errors |
| `detail` | Key=value context (counts, latency, model/provider, outcome) | As needed |

**Validation rules** (from FR-003–FR-005):

- Every entry carries `timestamp` and `level` — entries
  without them fail review.
- `ERROR` entries from exceptions MUST include the traceback
  (`logger.exception` or equivalent) — an error without a
  traceable cause fails review.
- `ERROR` entries MUST include `operation` — an error that
  does not identify the affected request/command/call fails
  review.

### Logging Configuration

The mode-dependent rule set (lives in Django settings for the
backend, build-time flag for the frontend):

| Field | Debug mode | Production mode |
|---|---|---|
| Threshold | `DEBUG` (everything emitted) | `INFO` (debug entries suppressed) |
| Destination | Captured standard streams | Captured standard streams |
| Routine success | Logged at `DEBUG`/`INFO` as appropriate | Silent (no per-request noise) |
| Warning / error | Always emitted | Always emitted |

**Validation rules** (from FR-001/FR-002/FR-010):

- Production output for a representative normal-operation
  window MUST contain zero `DEBUG` entries.
- Both modes MUST emit `ERROR` entries for the same failure.

### Redaction Rule

The set of value classes that MUST never appear in any entry
in any mode:

- Secrets and credentials: API keys (`MODEL_API_KEY`),
  `SECRET_KEY`, database passwords, tokens, authorization
  headers.
- Voice/audio bytes and transcripts.
- Journey questions, answers, and tool payload contents
  (only model/provider/latency/tool names are loggable).
- User-supplied free text beyond minimized identifiers.

**Validation rules** (from FR-006/FR-007):

- Verbose debug output passes through the same redaction —
  no bypass flag exists.
- A secrets sweep over captured output in both modes MUST
  find zero occurrences of secret, credential, or token
  values (SC-004).

## Relationships

```text
Logging Configuration --controls--> Log Entry (threshold per mode)
Redaction Rule --constrains--> Log Entry (all modes, no bypass)
Log Entry --describes--> operation (request / command / model call)
```

## State transitions

None — log entries are append-only fire-and-forget events.
A failure to emit an entry MUST NOT change the outcome of
the request, command, or response being processed (FR-008).
