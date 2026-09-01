# Setup Guide

## Prerequisites

- Python 3.11+
- Docker + Docker Compose (optional, for Postgres)

## 1. Clone & install

```bash
git clone https://github.com/mohdabrarbaloch-arch/day-25-imdaad.git
cd day-25-imdaad

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Configure

```bash
cp .env.example .env
```

Edit `.env` — at minimum set a strong `SECRET_KEY`:

```bash
SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(48))")
```

## 3. Run

```bash
python seed.py                    # creates tables + demo data
uvicorn app.main:app --reload     # dev server
```

- App: http://localhost:8000
- Swagger docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

## 4. Docker (Postgres)

```bash
docker compose up --build
```

The compose file runs PostgreSQL 16 + the API. Tables are auto-created on startup.

## 5. Environment variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | dev value | JWT signing secret — **must change in prod** |
| `DATABASE_URL` | `sqlite:///./imdaad.db` | SQLite or `postgresql+psycopg2://...` |
| `CORS_ORIGINS` | localhost | Comma-separated allowed origins |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 1440 | JWT lifetime |
| `RATE_LIMIT_REGISTER` | `5/minute` | Register rate limit |
| `RATE_LIMIT_LOGIN` | `10/minute` | Login rate limit |
| `RATE_LIMIT_REQUESTS` | `20/minute` | Request creation limit |
| `REQUEST_EXPIRY_HOURS` | 72 | Auto-expiry of open requests |

## 6. Production notes

- Use PostgreSQL, not SQLite, for real deployments.
- Set a long random `SECRET_KEY` and never commit `.env`.
- Rate limits are per-IP; behind a proxy, configure `X-Forwarded-For` handling.
