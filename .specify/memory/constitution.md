# Gonaj OSS Constitution

## Core Principles

### I. MVP Validation First (NON-NEGOTIABLE)

The MVP MUST be the smallest useful public-transport information product
that reaches users in Kochi and answers: "How do I get from A to B, and
when does the service operate?" Every feature proposal MUST demonstrate it
directly supports this validation question before it is accepted. Where
public-transport schedule data is unavailable during MVP development and
deployment, the validation question narrows to route/stop discovery and
service availability (see Principle VIII). Code and
infrastructure are disposable and MAY be replaced after validation; the
core data model and source provenance MUST be preserved so future
migration does not destroy useful information.

### II. Read-Only Public Product with Feedback

The public system MUST be read-oriented: users view stops, routes,
available schedule information, and search direct services, and report
discrepancies through a generic feedback mechanism. Schedule display and
the `WRONG_SCHEDULE` feedback category are active only where schedule
data exists (see Principle VIII). The MVP MUST NOT allow arbitrary users
to directly modify the canonical dataset. Feedback records MUST be
structured data with category (`WRONG_SCHEDULE`, `MISSING_STOP`,
`WRONG_ROUTE`, `ROUTE_NOT_OPERATING`, `OTHER`) and status (`new`,
`reviewed`, `dismissed`) so frequently reported routes and
stops are identifiable and can later feed an evidence-based
crowdsourcing system.

### III. Open Access Without Accounts; Minimal Data Collection

The public application MUST be usable without login, user accounts, or
user tracking. Feedback submission MUST NOT require authentication unless
a later, explicitly recorded decision demonstrates a clear need (e.g.
reputation, abuse control). No analytics or tracking capability may be
introduced merely because it is common; only minimal aggregate signals
(search counts, searches with/without results, feedback counts per
route/stop) MAY be collected, and the architecture MUST make data
minimisation straightforward.

### IV. Monorepo with Backend/Frontend Separation

The project MUST live in a single monorepo with a strict separation
between `backend/` (Django + Django REST Framework) and `frontend/`
(React + TypeScript). Cross-boundary communication MUST go through the
versioned REST API; neither side may reach into the other's internals,
build artefacts, or database. The system MUST remain a single deployable
application (web app + PostgreSQL/PostGIS); microservices are deferred
until a demonstrated requirement exists.

### V. Application-Owned GTFS-Inspired Data with Provenance (NON-NEGOTIABLE)

The application MUST maintain its own PostgreSQL + PostGIS dataset and
MUST NOT query OpenStreetMap live per user request; OSM data is imported
as a source, never used as the live database. The domain model MUST be
GTFS-inspired (`Agency`, `Route`, `Stop`, `Trip`, `StopTime`,
`ServiceCalendar`, plus `Feedback`, `Source`, `ImportRun`,
`OsmSnapshot`) even when no formal GTFS feed is exposed. Every
`OsmSnapshot` MUST carry `label`, `recipe_ref`, `source_timestamps`,
`retrieved_at`, and `imported_at`. Every transit record MUST retain source
provenance: source type, source reference/document, retrieval/import
date, OSM identifiers/version where applicable, and validity period where
applicable. Provenance MUST never be discarded during import.

### VI. Simple Synchronous Stack; Deferred Complexity

The MVP MUST stay on the simple synchronous stack and MUST NOT introduce
Kafka/event bus, event sourcing, Redis/Celery, Kubernetes, a dedicated
routing engine (OpenTripPlanner, GraphHopper, Valhalla), or full
multimodal journey planning. Data preparation MUST be Django management
commands (e.g. `import_osm_transit`, `import_schedule`) with OS-level
scheduling. A deferred technology may be introduced only when a concrete
MVP requirement justifies it and the justification is recorded as a
constitution amendment or superseding decision.

### VII. Django Admin as the Data Operations Interface

All internal data management (routes, stops, trips, schedules, feedback,
provenance records, import runs) MUST go through Django Admin. The project
MUST NOT build a separate administrative frontend during the MVP. Manual
review and correction workflows MUST be satisfiable through Admin alone.

### VIII. Schedule Data Availability Gates Schedule Features

Public-transport schedule data may be unavailable during MVP development
and deployment. Any feature that depends on schedule data — timetable
display, trip/service-calendar views, schedule search, and schedule
correction feedback — MUST be deferred to the next phase until real
schedule data is in hand. The MVP MUST NOT be blocked on, nor ship with,
placeholder or fabricated schedule content. Timetable entities (`Trip`,
`StopTime`, `ServiceCalendar`) remain part of the domain model so the
schema is ready, but populating and exposing them waits on data
availability. MVP validation proceeds on route/stop discovery, service
availability, and non-schedule feedback.

### IX. Meta AI Integration

AI features (passenger journey helper and feedback intelligence) MUST
call declared Meta models at runtime via a direct backend SDK; the
frontend MUST NOT call models directly. AI tools MUST be pure read-only
functions with JSON schemas; schemas MUST be MCP-compatible, but the MVP
MUST NOT stand up a separate MCP server.

The journey helper gives evidence-grounded connectivity answers only: no
schedules, no transfers, no invented times. It MUST refuse when the
answer is unknown, disambiguate stops when the request is ambiguous, and
link every cited route to its evidence at `/routes/:id`. Voice input via
Muse Voice Transcribe is an input mode only: the transcript MUST be
editable by the user, and no audio may be retained.

Feedback AI MAY suggest a feedback category and cluster likely
duplicates; it MUST NEVER auto-reject feedback or mutate canonical data.
Moderator triage remains human. Provenance Q&A is read-only over
`ImportRun` and `OsmSnapshot` records.

Every AI response MUST expose model ID, provider, and latency in API
response meta and in logs; MUST render distinctly as AI-generated in the
UI; and any AI-assisted report MUST be labelled unverified. AI features
MUST follow data minimisation: no tracking and no PII.

## Technology Stack & Architecture Constraints

The MVP stack is fixed: `backend/` is Django + Django REST Framework on
PostgreSQL + PostGIS; `frontend/` is React + TypeScript with Leaflet for
the interactive map (map-provider integration MUST stay isolated so the
implementation can change; MapLibre is the recorded alternative). The
public tile service MUST be OSM public tiles only for the small MVP, with
required attribution, appropriate self-identification, no bulk/prefetch
downloading, and a configurable tile-provider setting. The product MUST
NOT depend on the public Nominatim service for autocomplete; search MUST
be served from the application's own database of stops, localities, and
transport places. The initial transit search MUST cover direct services
only. No native mobile application (React Native or otherwise) is in MVP
scope; a responsive web frontend is the delivery target.

## Development Workflow & Compliance Gates

Every feature proposal MUST answer the handoff questions before
implementation: does it directly support MVP validation; does it fit
inside the existing Django/PostGIS/React architecture; does it preserve
source provenance; does it avoid introducing accounts, personal-data
collection, or full-crowdsourcing mechanics; does it avoid coupling to a
future architecture. Complexity beyond this constitution MUST be
justified against a current MVP requirement, not the eventual Gonaj
vision. MVP success MUST be judged by usefulness signals (successful
service discovery, repeated transport searches, corrective feedback,
user-reported usefulness) rather than raw traffic. Before public
deployment, Indian and Kerala privacy/legal requirements for anonymous
feedback and minimal data handling MUST be reviewed, and OSM usage-policy
and attribution compliance MUST be verified.

## Governance

This constitution supersedes all other practices for Gonaj OSS MVP work.
Amendments require a documented proposal, an explicit superseding
decision recorded against the affected principle, and a version bump per
the policy below; any deferred technology in Principle VI or the stack
section requires such an amendment before adoption. All reviews MUST
verify compliance with the principles above, and unjustified complexity
MUST be rejected. Versioning follows semantic versioning: MAJOR for
backward-incompatible governance or principle removals/redefinitions,
MINOR for new principles or materially expanded guidance, PATCH for
clarifications and wording fixes.

**Version**: 1.3.0 | **Ratified**: 2026-10-28 | **Last Amended**: 2026-10-28
