# Production deployment (single Ubuntu VPS + Cloudflare)

Target: `Ubuntu 20.04.6 LTS` 1GB RAM VPS with existing nginx on `80/443`.
Strategy: Docker for all runtimes; Cloudflare as edge only.

## Files

- [backend/Dockerfile.prod](../backend/Dockerfile.prod): `python:3.13-slim` + `gunicorn --workers 2 --threads 2`.
- [compose.prod.yml](../compose.prod.yml): `db` tuned for 1GB (`shared_buffers=128MB`, `effective_cache_size=512MB`, `max_connections=30`), `backend`, `web` (Caddy).
- [Caddyfile](../Caddyfile): `/api/*`, `/admin/*`, `/static/*` to `backend:8000`; `/*` to `frontend/dist`.
- [.env.prod.example](../.env.prod.example): copy to `.env.prod` on VPS only, never commit.

## Prereqs already in branch

- `gunicorn==23.0.0` in `backend/requirements.txt`.
- `STATIC_ROOT = BASE_DIR / "staticfiles"` in `backend/config/settings.py`.
- `.env.prod`, `caddy_data/` in `.gitignore` (`frontend/dist/` was already ignored).

## Deploy

```bash
# build frontend in CI, not on 1GB box
npm ci --prefix frontend && npm run build --prefix frontend
scp -r ./frontend/dist user@VPS:/opt/gonaj/frontend/dist
ssh user@VPS "cd /opt/gonaj && docker compose -f compose.prod.yml up -d --build"
ssh user@VPS "cd /opt/gonaj && docker compose -f compose.prod.yml exec backend python manage.py migrate"
ssh user@VPS "cd /opt/gonaj && docker compose -f compose.prod.yml exec backend python manage.py createcachetable"
ssh user@VPS "cd /opt/gonaj && docker compose -f compose.prod.yml exec backend python manage.py collectstatic --noinput"
```

Stop host nginx before Caddy binds `80/443`, or reuse host nginx instead of `web`.

Memory budget:

$$total \approx 250_{OS} + 250_{DB} + 2 \times 90_{workers} + 30_{caddy} \approx 710MB$$

```mermaid
flowchart LR
  User --> CF[Cloudflare Proxy]
  CF --> Caddy[Caddy :80/:443]
  Caddy --> BE[gunicorn x2 :8000]
  Caddy --> FE[static dist/]
  BE --> DB[(PostGIS tuned)]
```
