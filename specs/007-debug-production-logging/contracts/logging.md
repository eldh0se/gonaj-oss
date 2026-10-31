# Contract: Application Log Records

**Feature**: `007-debug-production-logging` | **Date**: 2026-10-31

This is the operator-facing contract for the log output both
application modes produce. It covers the **backend process
streams** (primary triage surface) and the **browser console
in development builds** (developer surface). Nothing here
changes any API response shape, error wording, or envelope —
those contracts are frozen and untouched.

## 1. Destinations

- Backend: process standard streams (stdout/stderr), captured
  by the deployment environment. No log files are written by
  the application.
- Frontend: browser console, development builds only
  (`import.meta.env.DEV`). Production builds emit nothing
  extra; user-visible errors render in the UI as today.

## 2. Entry format (backend)

```text
<TIMESTAMP> <LEVEL> <COMPONENT>: <MESSAGE> [KEY=VALUE ...]
```

- `TIMESTAMP`: UTC with a literal `Z` suffix, sortable across
  components regardless of machine timezone
  (e.g. `2026-10-31T06:30:01Z`).
- `LEVEL`: one of `DEBUG`, `INFO`, `WARNING`, `ERROR`.
- `COMPONENT`: logger name identifying the area
  (e.g. `apps.transport.api.errors`,
  `apps.journey.agent`, `apps.transport.importer`).
- `MESSAGE`: one human-readable line.
- `KEY=VALUE`: operation context
  (e.g. `method=GET path=/api/v1/routes/`,
  `model=muse-spark-1.3 provider=meta latency_ms=812`,
  `snapshot=kochi-2026-10 outcome=succeeded routes=42`).

## 3. Level usage

| Level | When used | Debug mode | Production mode |
|---|---|---|---|
| `DEBUG` | Fine-grained flow (request steps, import phases) | Emitted | Suppressed |
| `INFO` | Lifecycle and outcomes (startup, import summary, journey call meta) | Emitted | Emitted |
| `WARNING` | Routine client errors (4xx, throttling), recoverable anomalies | Emitted | Emitted, no traceback |
| `ERROR` | Server failures (5xx, unhandled exceptions, failed imports/tools) with traceback | Emitted | Emitted |

## 4. Guarantees

- **G-1**: Every `ERROR` entry identifies the affected
  operation (request method + path, command + snapshot, or
  model call) and includes the traceback.
- **G-2**: Routine successful operation in production mode
  produces no per-request entries.
- **G-3**: Emitting a log entry can never change a request,
  command, or response outcome.
- **G-4**: API response bodies are unchanged — stack details,
  identifiers, and internals never appear in responses even
  when they appear in logs.
- **G-5**: User-supplied free text appears in full only in
  `DEBUG` entries (debug mode only); entries at `INFO` and
  above carry at most the first 30 characters of any
  user-supplied value.

## 5. Redaction (all modes, no exceptions)

The following MUST never appear in any entry:

- API keys, secret keys, database passwords, tokens,
  authorization header values.
- Voice/audio bytes, transcripts, journey questions,
  journey answers, tool payload contents.
- User-supplied free text beyond the level-based rule:
  `DEBUG` entries (debug mode only) may carry the full value
  where diagnosis requires it (e.g. a failing search query);
  entries at `INFO` and above carry at most the first 30
  characters of any user-supplied value.
- Whole settings objects or whole request bodies
  (at every level, including `DEBUG`).

Loggable journey context is limited to: model id, provider,
latency, tool names — per the existing journey precedent.

## 6. Examples

Debug-mode flow (illustrative):

```text
2026-10-31T06:30:01Z DEBUG apps.transport.api.views: route_list search='kochi' count=3 method=GET path=/api/v1/routes/
2026-10-31T06:30:01Z INFO apps.journey.agent: journey model=muse-spark-1.3 provider=meta latency_ms=812 tools_used=find_routes
```

Production failure (illustrative):

```text
2026-10-31T06:35:44Z ERROR apps.core.error_signals: api error status=500 method=POST path=/api/v1/journey/
Traceback (most recent call last):
  ...
```

Import outcome (illustrative):

```text
2026-10-31T06:40:00Z INFO apps.transport.management.commands.import_osm_snapshot: import outcome=succeeded snapshot='kochi-2026-10' stops=318 routes=42
2026-10-31T06:40:00Z ERROR apps.transport.management.commands.import_osm_snapshot: import outcome=aborted snapshot='kochi-2026-10' fatal=REQUIRED_FILE_MISSING report=./osm-import-report.json
```

## 7. Frontend entries (development builds)

- Development builds log API diagnostics via `console.debug`
  only, through one gated helper — the equivalent of a
  `DEBUG`-level backend entry. Production builds emit
  nothing (the helper is eliminated from the bundle).
- Entry shape: one line carrying the operation (e.g.
  `search-stops`, `get-route`), the request path, the
  outcome (status code or `network-error`), and latency
  where known.
- Redaction follows the same level-based rule: this surface
  is `DEBUG`-equivalent and dev-only, so a full query string
  is permitted where diagnosis requires it; response bodies
  are never logged wholesale; journey questions, answers,
  and transcripts are never logged.

## 8. Out of scope

- Retention, rotation, aggregation, and alerting (deployment
  environment's job).
- Log-based metrics or analytics beyond the minimal
  aggregate signals the project already permits.
- Any change to API response contracts or error wording.
