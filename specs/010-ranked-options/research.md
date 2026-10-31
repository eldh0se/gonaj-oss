# Research: Ranked Journey Options

**Feature**: [spec.md](spec.md) | **Date**: 2026-10-31 | **Branch**: `010-ranked-options`

No NEEDS CLARIFICATION remained: the requester fixed the slice (same agent + 008/009 tools; group verified pairs by `operator`; order by fewest stops then route id; boarding text from `resolved_origin` + `stop.name` only; destination list capped at 5; verifier and repair nudge unchanged; KSRTC/mixed/no-times tests). Each decision below records what was chosen, why, and what was set aside.

## Decision: Rank in the agent over `find_routes_matrix` output, grouped by annotated operator

- **Decision**: After the matrix returns viable pairs, `agent.py` groups pairs by `route.operator` (the existing `routes_with_master_fields` annotation; null/blank operators form a plainly labelled group) and orders pairs within each group by route stop count ascending, then route id ascending. Groups order by operator name with the unknown-operator group last.
- **Rationale**: Fewest-stops-first is a deterministic, explainable proxy for directness that needs no schedule data (constitution VIII); route id breaks ties stably for unchanged data. Operator comes from the same annotation the 003 list already serves, so no new query or model involvement.
- **Alternatives considered**: Fewest-transfers or fastest-first ranking (rejected — schedule-gated, no data); model-chosen ordering (rejected — model is the eloquence layer, never the source of truth; order must be verifiable).

## Decision: Boarding text from `resolved_origin` + `stop.name` only, no stand table

- **Decision**: A boarding hint names the boarding stop and, when the 006 `resolved_origin` annotation is non-empty, the origin context; nothing else. No stand/side mapping table is built.
- **Rationale**: FR-005 allows hints only where the dataset supports them. `stop.name` + `resolved_origin` are the only boarding facts the canonical data guarantees; a stand table would be invented data for most stops and a maintenance burden.
- **Alternatives considered**: Stand/side mapping table (rejected — invents data, violates FR-005); omitting hints entirely (rejected — spec US2 requires guidance where supported).

## Decision: Destination list capped at 5, every entry evidence-linked

- **Decision**: When the destination place has several reachable members, the answer lists up to 5 member options (matrix order), each with its `/routes/:id` evidence link; the count of further options is stated, never listed.
- **Rationale**: Bounds payloads for hub places while satisfying FR-006 (offer reachable members, never force one). Cap of 5 matches a readable answer length.
- **Alternatives considered**: Uncapped lists (rejected — hub groups could dump dozens of options); cap of 1 (rejected — reintroduces forced guessing).

## Decision: Verifier, repair nudge, and `_FORBIDDEN_SHAPED` unchanged

- **Decision**: Every ranked option passes the existing `_verify_route` travelling-order check; drafts with time/transfer-shaped content get the same one repair attempt, then refusal.
- **Rationale**: 010 widens the answer from one option to all verified options; the evidence and no-times guarantees must hold per option, so the existing gate runs per option unchanged.
- **Alternatives considered**: Relaxing verification for lower-ranked options (rejected — unverifiable options are exactly what refusal exists for).

## Decision: Additive answer fields, existing clients unaffected

- **Decision**: The `ok` payload keeps `answer`, `boarding_stop`, `alighting_stop`, `routes`, and `meta`; it gains `option_groups` (per-operator ranked options) and `destinations` (capped reachable members). The prose `answer` enumerates the groups so old renderers still read correctly.
- **Rationale**: Additive-only contract change, same policy as 008; frontend can adopt the structured fields incrementally without breaking current rendering.
