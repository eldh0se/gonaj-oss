# gonaj-oss

The name Gonaj is short for "Go on a journey". Gonaj is an open-source
public-transport information project, initially focused on the
Kochi/Greater Cochin region of Kerala, India. Gonaj exists to make
public-transport information easier to discover and understand.

## The idea

Public-transport schedule and route information is hard to find in one
place. Gonaj aims to fix that with a simple web portal: a map where users
can select an origin and a destination and see the available
public-transport options, with schedule information where it exists.

The project has two ultimate goals:

1. Make public-transport schedule information easily accessible to users.
2. Make it easy for users to contribute information and corrections
   (crowdsourced data).

## MVP

The current phase is a minimal viable product whose purpose is to validate
whether the product is useful to end users — not to build the final Gonaj
architecture. The MVP is deliberately read-oriented:

- Browse public-transport stops and routes on a map.
- Search for available transport options between an origin and
  a destination.
- View schedule information where schedule data is available.
- Ask the journey helper for connectivity answers grounded in published
  data (no schedules, no invented times), by text or voice input.
- Report discrepancies (wrong route, missing stop, route not operating,
  and similar) through a generic feedback mechanism. AI may suggest a
  category, but moderation stays human.

What the MVP is **not**: direct crowdsourced editing of the dataset,
user accounts or login, realtime vehicle tracking, multimodal journey
planning, or a mobile app. Those are deferred until validation shows
they are needed.

Because schedule data may not be available during MVP development and
deployment, schedule-dependent features (timetable display, schedule
search, schedule-correction feedback) are deferred to the next phase.
The timetable data model is designed up front so the schema is ready when
the data arrives.

## Architecture

A single monorepo with a strict separation between `backend/` and
`frontend/`, communicating over a versioned REST API. The system is one
deployable application, not microservices.

| Area | Decision |
|---|---|
| Frontend | React + TypeScript, Leaflet map |
| Backend | Django + Django REST Framework |
| Database | PostgreSQL + PostGIS |
| Data operations | Django Admin |
| Transit model | GTFS-inspired |
| Geographic source | OpenStreetMap snapshot import (offline, provenance-tracked) |
| Schedule source | Official / RTI-derived / manually curated data |
| AI assistance | Meta models via backend SDK; read-only tools; output labelled unverified |

The application maintains its own database: OpenStreetMap is treated as a
source of geographic/transit data to be imported, not as the live
database. Each import is captured as a versioned OSM snapshot, and source
provenance (source type, references, import dates, OSM identifiers) is
preserved on records from the beginning so a future evidence-based system
can build on it. AI features call Meta models from the backend through
read-only tools; every AI response is rendered distinctly and labelled
unverified, with model, provider, and latency exposed in the API.

The site is usable without login or user tracking. Data collection is
limited to minimal aggregate signals needed for validation.

## Repository layout

```text
backend/    Django application (API + Django Admin)
frontend/   React + TypeScript web application
docs/       Project documentation
.specify/   Spec Kit artefacts (see project constitution)
```

The governing decisions live in the project constitution at
`.specify/memory/constitution.md`. Feature work should be checked against
it before implementation.

## Status

Early MVP development. The project has not yet reached end users, and the
initial dataset (OSM import plus official schedule data) is still being
assembled. To run the backend from a fresh clone, follow
[docs/setup-backend.md](docs/setup-backend.md).
The public read-only transport API (routes, stops, direct
connectivity) is documented in
[docs/read-map-api.md](docs/read-map-api.md).
Further setup and contribution instructions will be added alongside each
feature as it is implemented.

## License

See [LICENSE](LICENSE).
