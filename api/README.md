# AboveDeck API

FastAPI backend for AboveDeck. Deploy as a Render Web Service.

## Local development

```bash
cd api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

- `GET /health` — always returns 200
- Data endpoints return 503 until `DATABASE_URL` is set

## Render Web Service

| Setting | Value |
|---------|--------|
| Root Directory | `api` |
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `python3 -m uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/health` |

### Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `CORS_ORIGINS` | No | Comma-separated allowed origins (set to your static site URL on Render) |
| `DATABASE_URL` | No (for now) | Neon Postgres connection string; unset = data endpoints return 503 |

## Neon (later)

1. Enable PostGIS in Neon
2. Set `DATABASE_URL` on Render
3. Add `sqlalchemy[asyncio]` and `asyncpg` to `requirements.txt`
4. Implement queries in `db.py` and route handlers
