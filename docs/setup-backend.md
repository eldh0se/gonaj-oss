# Backend setup (fresh clone)

Proves User Story 1: from a clean machine to a running server with a
working admin login, following only this guide. Part of
`specs/001-scaffold-admin`.

## Prerequisites

- Python 3.13+
- A container runtime for `compose.yml` (Docker Desktop or compatible)
- Node 18+ and npm (frontend placeholder only)

## 1. Create the project environment

From the repository root:

```sh
uv venv --python 3.13      # creates .venv/ at the repo root
source .venv/bin/activate
```

Without `uv`:

```sh
python3.13 -m venv .venv
source .venv/bin/activate
```

## 2. Install backend dependencies

```sh
pip install -r backend/requirements-dev.txt
```

## 3. Configure the environment

Copy these into your shell (development values only — never commit
real secrets):

```sh
export DJANGO_SECRET_KEY=dev-only-insecure-key
export POSTGRES_DB=gonaj
export POSTGRES_USER=gonaj
export POSTGRES_PASSWORD=gonaj
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
```

`DJANGO_SECRET_KEY` is required: starting without it fails fast
naming the variable. Optional overrides: `DJANGO_DEBUG` (default `1`),
`DJANGO_ALLOWED_HOSTS` (default `localhost,127.0.0.1`).

## 4. Start the database

```sh
docker compose up -d db
```

This starts PostgreSQL 16 (PostGIS pre-enabled for the later spatial
feature) with a persistent `pgdata` volume.

## 5. Apply migrations

```sh
cd backend
./manage.py migrate
```

Expected: all migrations apply cleanly. Re-running is a safe no-op.

## 6. Create the admin account

```sh
./manage.py createsuperuser
```

Follow the prompts. This is the internal operations account for
Django Admin; there are no public user accounts.

## 7. Run the server

```sh
./manage.py runserver
```

Expected: serving on http://127.0.0.1:8000/.

## 8. Verify

- Admin login: open http://127.0.0.1:8000/admin/login/ and log in
  with the superuser. The dashboard lists the administration views.
  Wrong credentials are denied with an error and no session.
- API root: `curl http://127.0.0.1:8000/api/v1/` returns
  `{"name":"gonaj","version":"v1"}`. Unknown versions
  (e.g. `/api/v9/`) return 404.
- Test suite: `./manage.py test` runs the backend checks that CI
  also runs on every pull request.

## Frontend placeholder (optional)

```sh
cd frontend
npm install
npm run dev     # serves with /api proxied to localhost:8000
```

The placeholder page shows the backend API-root status. The real map
UI arrives with the first transport feature.

## Troubleshooting

- **Database unreachable / connection refused**: `docker compose up -d
  db` may still be initialising — wait and retry. Confirm the port
  (`5432`) is free and the `POSTGRES_*` values match `compose.yml`.
- **`ImproperlyConfigured: Missing required environment variable`**:
  export the named variable (step 3); `DJANGO_SECRET_KEY` has no
  default on purpose.
- **Port already in use**: runserver's `8000` or the db's `5432` is
  taken — stop the other process or remap the published port.
- **Migration failure after pulling new code**: run `./manage.py
  migrate` again; if CI's `makemigrations --check` fails on your
  branch, a model change is missing its migration.
