# AboveDeck API

FastAPI backend for AboveDeck. Deploy as a Render Web Service.

## Local development

```bash
cd api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

- `GET /health` — always returns 200; includes DB connectivity and keepalive cron status
- Data endpoints return 503 until `DATABASE_URL` is set

Point the map at a local API by editing [`assets/config.js`](../assets/config.js) (`apiBaseUrl: 'http://localhost:8000'`). Serve `index.html` over http (Live Server), not `file://`.

## Keepalive cron

GitHub Actions workflow [`.github/workflows/keepalive.yml`](../.github/workflows/keepalive.yml) pings `GET /health?source=keepalive` every 10 minutes so the Render free-tier API stays warm. The health response exposes `keepalive_status` (`ok` / `stale` / `unknown`) and `keepalive_last_ping_at` for the system status page.

The first map load after idle can still take up to a minute. The frontend pings `/health` and retries before showing an error.

## Render Web Service

| Setting | Value |
|---------|--------|
| Root Directory | `api` |
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `python3 -m uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/health` |

### Environment variables (required for the live map)

Set these on the **abovedeck-web-service** dashboard. Existing values are not always overwritten by [`render.yaml`](../render.yaml).

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | Neon connection string. Use `sslmode=require` (not `ssl=require`). Example: `postgresql://USER:PASS@HOST/neondb?sslmode=require` |
| `CORS_ORIGINS` | Yes | Comma-separated browser origins allowed to call the API |

**CORS_ORIGINS checklist**

```
https://dashkim.github.io,http://localhost:8000,http://127.0.0.1:8000,http://localhost:5500,http://127.0.0.1:5500
```

- GitHub Pages origin is `https://dashkim.github.io` even when the path is `/AboveDeck/`.
- Add any other origin you actually use (custom domain, another Live Server port).
- After changing env vars, wait for Render to finish deploy, then hard-refresh the map.

If the left panel says the origin is blocked, the page origin is missing from `CORS_ORIGINS`. If it says the API is asleep, wait and click **Refresh this area**. If it mentions `DATABASE_URL`, the API is up but Neon is not configured on Render.
