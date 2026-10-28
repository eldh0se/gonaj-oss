# Feature Specification: Backend Admin Scaffold

**Feature Branch**: `001-scaffold-admin`

**Created**: 2026-10-28

**Status**: Draft

**Input**: User description: "scaffold-admin: Runnable Django + DRF /api/v1/ + PostgreSQL with Django admin login. Fresh-clone install, migrate, createsuperuser, run. No transport logic. CI checks on PR."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run the backend from a fresh clone (Priority: P1)

A developer clones the repository on a clean machine, installs the
backend dependencies, applies database migrations, creates an admin
(superuser) account, and starts the development server — using only the
steps written in the project docs.

**Why this priority**: Nothing else can be built or verified until the
backend runs reproducibly from a fresh checkout. This is the foundation
every later feature stands on.

**Independent Test**: On a machine without the project installed, follow
the documented steps in order; the server starts with no manual
workarounds, and each step succeeds as documented.

**Acceptance Scenarios**:

1. **Given** a fresh clone with no prior setup, **When** the developer
   follows the documented install steps, **Then** all backend
   dependencies install without errors.
2. **Given** installed dependencies and a reachable database, **When**
   the developer runs migrations, **Then** all migrations apply cleanly
   with no errors.
3. **Given** migrated database, **When** the developer creates a
   superuser through the documented command, **Then** the account is
   created and usable.
4. **Given** a migrated database, **When** the developer starts the
   server, **Then** it serves requests on the documented address.

---

### User Story 2 - Log into Django Admin (Priority: P1)

An internal operator opens the admin interface in a browser and logs in
with the superuser account to confirm the data-operations interface is
available for future manual curation work.

**Why this priority**: The constitution designates Django Admin as the
sole internal data-management interface; proving login works now
de-risks all future manual data work.

**Independent Test**: Log in with the superuser credentials created in
User Story 1; the admin dashboard loads and lists the administration
views.

**Acceptance Scenarios**:

1. **Given** a running server and a superuser account, **When** the
   operator submits valid credentials at the admin login page, **Then**
   the admin dashboard loads successfully.
2. **Given** a running server, **When** someone submits invalid
   credentials at the admin login page, **Then** access is denied with
   an error message and no session is created.

---

### User Story 3 - Reach the versioned API root (Priority: P2)

A frontend developer sends a request to the versioned API root and
receives a successful response confirming the API layer is wired and
versioned, before any transport endpoints exist.

**Why this priority**: It proves the REST contract point between the
future React frontend and the backend exists and is versioned from day
one, without waiting for domain logic.

**Independent Test**: Issue an HTTP request to the `/api/v1/` root
against the running server; receive a successful response identifying
the API version.

**Acceptance Scenarios**:

1. **Given** a running server, **When** a client requests `/api/v1/`,
   **Then** the server returns a success response identifying version 1.
2. **Given** a running server, **When** a client requests an unknown
   version prefix such as `/api/v9/`, **Then** the server returns a
   not-found response.

---

### User Story 4 - Automated checks run on every pull request (Priority: P3)

A contributor opens a pull request and automated checks (dependency
install, migration check, test suite) run against it, reporting
pass/fail before merge.

**Why this priority**: Protects the scaffold from regressions as
feature work begins; lower priority only because it guards future work
rather than enabling today's.

**Independent Test**: Open a pull request; the checks execute
automatically and their results are visible on the pull request.

**Acceptance Scenarios**:

1. **Given** an open pull request, **When** the checks finish on a
   healthy branch, **Then** all checks report success on the pull
   request.
2. **Given** an open pull request containing a broken migration,
   **When** the checks finish, **Then** at least one check reports
   failure on the pull request.

---

### Edge Cases

- What happens when the database is unreachable at server startup?
  The failure must be a clear, actionable error (not a stack trace
  alone) so the developer knows to start or configure the database.
- How does setup behave when migrations have already been applied?
  Re-running migrations must be a safe no-op, not an error.
- What happens when required configuration (e.g. database connection)
  is missing? The system must fail fast with a message naming the
  missing setting.
- How do CI checks behave when dependency installation itself fails?
  The run must report failure clearly rather than silently passing with
  skipped steps.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The `backend/` directory MUST contain a runnable web
  application project as the single backend of the monorepo.
- **FR-002**: The backend MUST serve its API under the versioned prefix
  `/api/v1/`, and the version root MUST return a success response.
- **FR-003**: PostgreSQL MUST be the database backend, with the
  connection fully configurable through environment settings (no
  hardcoded credentials).
- **FR-004**: The Django Admin interface MUST be enabled, and superuser
  creation through the documented command MUST produce an account able
  to log in.
- **FR-005**: A fresh-clone flow (install dependencies, apply
  migrations, create superuser, run server) MUST be documented and MUST
  succeed end-to-end on a clean machine following only those docs.
- **FR-006**: Automated checks MUST run on every pull request and MUST
  cover at minimum dependency installation, migration validity, and the
  backend test suite; results MUST be visible on the pull request.
- **FR-007**: This feature MUST NOT introduce any transport-domain
  models, endpoints, or data (no routes, stops, trips, or schedules).
- **FR-008**: The public application surface in this feature MUST NOT
  require user accounts; only the internal admin login requires
  credentials.

### Key Entities

- **Admin Account**: The internal superuser used to access Django Admin
  for future manual data curation. Attributes: username, usable login
  state. No public-user accounts exist in this feature.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer unfamiliar with the project goes from fresh
  clone to logged-in admin dashboard in under 30 minutes by following
  only the written docs.
- **SC-002**: 100% of fresh-clone setup attempts following the docs
  reach a running server with no undocumented manual steps.
- **SC-003**: The versioned API root answers successfully on every
  running instance; unknown version prefixes are rejected.
- **SC-004**: Every pull request receives automated check results
  before it is eligible for merge, with zero PRs merged on unknown
  check status during the evaluation period.
- **SC-005**: Review confirms the codebase contains no
  transport-domain logic, keeping the scaffold clean for feature work.

## Assumptions

- Local PostgreSQL for development is provided via a container
  definition shipped with the repo (documented in the setup flow), with
  connection details supplied through environment settings.
- Continuous integration runs on the same platform that hosts the
  repository's pull requests (GitHub Actions if hosted on GitHub).
- The documented setup flow targets a Unix-like development machine.
- Database migrations are the only supported schema-change mechanism;
  manual database edits are out of scope.
- Admin login is an internal operations interface only; it creates no
  obligation for public user accounts (per constitution Principle III).
