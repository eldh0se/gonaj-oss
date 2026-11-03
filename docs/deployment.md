# Production deployment (single VPS + Cloudflare)

Target: single small VPS (Docker, Cloudflare edge).
Strategy: Docker for all runtimes; Cloudflare as edge only.

## Files

- [backend/Dockerfile.prod](../backend/Dockerfile.prod): `python:3.13-slim` + `gunicorn --workers 2 --threads 2`.
- [compose.prod.yml](../compose.prod.yml): tuned `db` (`shared_buffers=128MB`, `effective_cache_size=512MB`, `max_connections=30`), `backend`, `web` (Caddy).
- [Caddyfile](../Caddyfile): `/api/*`, `/admin/*`, `/static/*` to `backend:8000`; `/*` to `frontend/dist`.
- [.env.prod.example](../.env.prod.example): copy to `.env.prod` on VPS only, never commit.

## Prereqs already in branch

- `gunicorn==23.0.0` in `backend/requirements.txt`.
- `STATIC_ROOT = BASE_DIR / "staticfiles"` in `backend/config/settings.py`.
- `.env.prod`, `caddy_data/` in `.gitignore` (`frontend/dist/` was already ignored).

## Deploy

```bash
# build frontend in CI, not on the VPS
npm ci --prefix frontend && npm run build --prefix frontend
scp -r ./frontend/dist user@VPS:/opt/gonaj/frontend/dist
ssh user@VPS "cd /opt/gonaj && docker compose -f compose.prod.yml up -d --build"
ssh user@VPS "cd /opt/gonaj && docker compose -f compose.prod.yml exec backend python manage.py migrate"
ssh user@VPS "cd /opt/gonaj && docker compose -f compose.prod.yml exec backend python manage.py createcachetable"
ssh user@VPS "cd /opt/gonaj && docker compose -f compose.prod.yml exec backend python manage.py collectstatic --noinput"
```

Stop any host web server bound to `80/443` before Caddy starts, or reuse host web server instead of `web`.

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

## Production hardening (abuse budgets)

Per-IP throttle budgets and request size caps are enforced in the app and tuned
entirely through env (see [.env.prod.example](../.env.prod.example));
`DEBUG` stays off and `ALLOWED_HOSTS` stays set to the serving domain(s).

- `TRANSPORT_TRUSTED_PROXY` stays `caddy` (the known proxy only). Per-IP identity
  follows the forwarded address solely on that trust; never wildcard it, or any
  client can spoof its IP and dodge budgets.
- Cloudflare and Caddy stay dumb pipes: no edge rate limiting. The app budgets
  (`journey_min/day`, `transcribe_min/day`) are the single source of truth, so
  all rejections stay in the API's plain-language 429/400 shapes.
- Budgets are per public IP. Mobile users in Kochi share addresses behind CGNAT,
  so one heavy sharer can consume the shared slice (notably the 1500/day journey
  budget). Keep the defaults, watch 429 rates per endpoint, and tune via env —
  tighten against bursty abuse first, raise budgets only if legitimate users get
  throttled.
- Defaults: journey 60/min + 1500/day, transcribe 20/min + 300/day; caps: question
  500 chars, history 10 turns × 500 chars, context 8KB, audio 5MB WAV-only.
