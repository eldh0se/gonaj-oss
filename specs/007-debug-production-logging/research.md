# Research: Debug and Production Logging

**Feature**: `007-debug-production-logging` | **Date**: 2026-10-31

All context below was established by direct inspection of the
repository (settings, views, agent, providers, importer, frontend
API layer, prior plans). No open questions remain; there were no
`NEEDS CLARIFICATION` items in the Technical Context.

## Current state

- `backend/config/settings.py` defines `DEBUG` from `DJANGO_DEBUG`
  but configures **no** `LOGGING` — Django defaults apply
  (root WARNING to stderr; `django.server` request lines only
  under `runserver`).
- Partial logging already exists and sets the project precedent:
  `backend/apps/journey/agent.py` and
  `backend/apps/journey/views.py` use
  `logging.getLogger(__name__)` with `logger.info(...)` for
  model/provider/latency/tools and `logger.exception(...)` on
  transcription, tool, and model-loop failures. The journey
  docstrings already state the redaction rule: logs carry
  model, provider, latency, tools — never questions, answers,
  transcripts, or audio.
- `backend/apps/transport/api/views.py`,
  `backend/apps/transport/api/errors.py`, and the
  `import_osm_snapshot` management command emit **no** log
  records. API errors are rendered plain-language by
  `plain_exception_handler`; stack details must stay out of
  responses (existing contract, unchanged by this feature).
- Frontend (`frontend/src/api/client.js`, `journey.js`) has no
  logging calls; tests run under Vitest, dev/build via Vite.

## Decisions

### Decision 1: Backend mechanism — Django `LOGGING` dict, console only

- **Decision**: Configure the standard Django `LOGGING` dict in
  `backend/config/settings.py` using stdlib `logging` only:
  one `StreamHandler` to the captured standard streams,
  threshold `DEBUG` when `DEBUG` is true else `INFO`, with a
  formatter carrying timestamp, level, logger name, and message.
- **Rationale**: Zero new dependencies (constitution VI);
  12-factor compatible — `compose.yml`, systemd, and CI all
  capture process streams, and retention/rotation stays with
  the environment per the spec assumption.
- **Alternatives considered**: File handlers (rejected — disk
  management becomes the app's problem and risks filling
  disks, contradicting the bounded-volume edge case);
  `structlog`/JSON logging packages (rejected — new
  dependency and format churn for MVP-scale triage; plain
  lines are greppable and sufficient; revisit post-MVP if a
  log aggregator requires JSON).

### Decision 2: Keep and extend the existing journey logging pattern

- **Decision**: Keep the `logging.getLogger(__name__)` +
  `logger.info`/`logger.exception` precedent from the journey
  code and apply the same shape at the remaining error
  boundaries (transport API 5xx path, import command outcome).
  No new logging abstraction or wrapper module.
- **Rationale**: Consistency with the only established
  in-repo pattern; smallest possible new surface.
- **Alternatives considered**: A shared `apps.core.logging`
  helper with custom LoggerAdapter injecting request context
  (rejected — adds indirection for fields the call sites
  already pass explicitly; revisit if correlation IDs are
  ever required).

### Decision 3: Redaction by explicit denylist + never-log rules

- **Decision**: Redact an explicit key set wherever mappings
  are logged (`MODEL_API_KEY`, `SECRET_KEY`, database
  password, `password`, `token`, `authorization`, audio bytes)
  and keep the standing never-log rules: never log settings
  values wholesale, never log request bodies, never log
  journey questions/answers/transcripts/audio (constitution
  IX). Debug verbosity must pass through the same redaction.
- **Rationale**: FR-006/FR-007 and constitution III/IX make
  safety a hard requirement; a denylist at the format site
  plus never-log rules at call sites is the simplest shape
  that survives verbose mode.
- **Alternatives considered**: Allowlist-only structured
  logging (rejected — heavier refactor of existing
  `logger.info("... model=%s ...")` call sites for no MVP
  benefit).

### Decision 4: Level policy per mode

- **Decision**: `DEBUG=true` → root/console threshold `DEBUG`
  (fine-grained flow visible); production (`DEBUG` false) →
  threshold `INFO`, with routine per-request success staying
  silent and warnings/errors always emitted. 4xx API
  outcomes (routine client errors, throttling) log at most at
  `WARNING` without tracebacks; 5xx and unhandled exceptions
  log at `ERROR` with `logger.exception` (traceback included).
- **Rationale**: Directly implements FR-001/FR-002/FR-010 and
  SC-003 (no debug noise in production; errors stand out).
- **Alternatives considered**: Uniform level in both modes
  (rejected — violates the core request); per-view log
  silencing lists (rejected — unnecessary while routine
  success paths simply don't log).

### Decision 5: Frontend — tiny `import.meta.env.DEV`-gated debug helper

- **Decision**: Add a minimal debug helper in the frontend API
  layer that calls `console.debug` only when Vite's built-in
  `import.meta.env.DEV` is true (dead-code-eliminated from
  production builds). Production keeps today's behaviour:
  errors surface in the UI; nothing extra is logged.
- **Rationale**: Zero dependencies, build-time gating (cannot
  leak into production bundles), matches the spec's
  mode-dependent verbosity for the second codebase surface.
- **Alternatives considered**: A logging library or remote
  error reporting (rejected — new dependency/service,
  tracking implications under constitution III, and no MVP
  requirement).

### Decision 6: Operation context without new middleware

- **Decision**: Error entries identify the operation via
  already-available values (view/module logger name, request
  path and method at the API boundary, command name and
  snapshot label for imports, model/provider/latency for
  journey). No request-ID middleware, no stored correlation
  state.
- **Rationale**: Satisfies FR-005's "traceable identifier"
  with zero new infrastructure (constitution VI) and zero
  stored per-request state (constitution III).
- **Alternatives considered**: UUID-per-request middleware
  propagated through logs (rejected — stateless per-request
  design has no place to thread it without middleware and
  adapter machinery; revisit if triage proves path+time
  insufficient).

### Decision 7: Accept unbounded error output under spikes

- **Decision**: No throttling, sampling, or dedup of repeated
  error entries. Under an error spike (e.g. a hot loop of
  5xx), every failure is recorded; `ERROR` entries are never
  suppressed. This resolves the spec's spike edge case by
  explicit acceptance rather than mitigation.
- **Rationale**: Suppressing errors risks hiding outages —
  the worst possible triage failure. MVP traffic is small,
  retention stays with the deployment environment, and
  routine success paths remain silent, so steady-state
  volume is still bounded (FR-010).
- **Alternatives considered**: Error dedup/rate-limiting
  (rejected — new machinery plus the risk of dropping the
  one entry that explains an outage; revisit post-MVP if a
  real flood is observed).
