# Imdaad (امداد) — Architecture

## Overview

Imdaad is a blood donation network for Pakistan. It connects **donors** with **urgent blood requests** posted by hospitals or patient families. The core value is a real **ABO/Rh compatibility engine** that finds every eligible donor for a request within seconds, so nobody has to make 50 phone calls during an emergency.

## System Diagram

```
                        ┌─────────────────────────────┐
                        │         Browser (SPA)        │
                        │  mobile-first vanilla JS     │
                        └──────────────┬──────────────┘
                                       │ HTTPS (JSON)
                                       ▼
                        ┌─────────────────────────────┐
                        │        FastAPI (Uvicorn)     │
                        │  /api/v1/...                 │
                        │  - auth (JWT + bcrypt)       │
                        │  - donors (profiles, search) │
                        │  - requests (lifecycle)      │
                        │  - offers (donor → request)  │
                        │  - stats                     │
                        │  SlowAPI rate limits         │
                        └──────────────┬──────────────┘
                                       │ SQLAlchemy 2.0 (ORM)
                                       ▼
                        ┌─────────────────────────────┐
                        │        Database              │
                        │  SQLite (dev, WAL)           │
                        │  PostgreSQL 16 (Docker/prod) │
                        └─────────────────────────────┘
```

## Tech Stack

| Layer       | Technology                                    |
|-------------|-----------------------------------------------|
| API         | FastAPI 0.115 · Python 3.11 · Pydantic v2     |
| ORM         | SQLAlchemy 2.0 (typed models, scoped queries) |
| Auth        | JWT (HS256, 24h) · bcrypt (12 rounds) · SlowAPI rate limits |
| Database    | SQLite (dev, WAL mode) · PostgreSQL 16 (docker-compose) |
| Frontend    | Vanilla JS SPA · mobile-first dark theme · zero build step |
| Infra       | Docker · docker-compose · Vercel-ready (`api/index.py`) |
| CI          | GitHub Actions (lint + tests)                 |

## Data Model

### users
- id, email (unique), password_hash, full_name, phone, role (`donor` | `requester` | `admin`), city, is_active, created_at

### donor_profiles
- id, user_id (FK, unique), blood_group (`A+ A- B+ B- AB+ AB- O+ O-`), last_donation_date (nullable), is_available (bool), medical_notes (text), donation_count, created_at, updated_at

### blood_requests
- id, request_number (`IMD-2026-000001`, unique per year), patient_name, blood_group, units (int 1–20), city, hospital (nullable), urgency (`normal` | `urgent` | `emergency`), status (`open` → `matched` → `fulfilled` | `cancelled` | `expired`), created_by (FK user), note, created_at, updated_at, expires_at

### offers
- id, request_id (FK), donor_id (FK user), status (`pending` → `accepted` | `declined` | `withdrawn`), message, created_at
- Unique constraint (request_id, donor_id) — one offer per donor per request

## Blood Compatibility Engine (`app/compat.py`)

Pure function `can_donate(donor: str, recipient: str) -> bool` implementing ABO + Rh rules:

| Donor \ Recipient | A+ | A- | B+ | B- | AB+ | AB- | O+ | O- |
|-------------------|----|----|----|----|-----|-----|----|----|
| A+                | ✅ | ❌ | ❌ | ❌ | ✅  | ❌  | ❌ | ❌ |
| A-                | ✅ | ✅ | ❌ | ❌ | ✅  | ✅  | ❌ | ❌ |
| B+                | ❌ | ❌ | ✅ | ❌ | ✅  | ❌  | ❌ | ❌ |
| B-                | ❌ | ❌ | ✅ | ✅ | ✅  | ✅  | ❌ | ❌ |
| AB+               | ❌ | ❌ | ❌ | ❌ | ✅  | ❌  | ❌ | ❌ |
| AB-               | ❌ | ❌ | ❌ | ❌ | ✅  | ✅  | ❌ | ❌ |
| O+                | ✅ | ❌ | ✅ | ❌ | ✅  | ❌  | ✅ | ❌ |
| O-                | ✅ | ✅ | ✅ | ✅ | ✅  | ✅  | ✅ | ✅ |

Universal donor: **O-** · Universal recipient: **AB+**.

## Request Lifecycle

```
 open ──► matched ──► fulfilled
   │         │
   ├─► cancelled      (requester/admin)
   └─► expired        (auto: expires_at < now, or manual by admin)
```

- `open`: anyone with a donor profile can view and offer.
- `matched`: requester or admin accepted at least one offer (request frozen — no new offers).
- `fulfilled`: donation completed (units met). Terminal state.
- `cancelled` / `expired`: terminal states. Illegal transitions → **409**.
- Unknown status values → **422**. Foreign access → **404** (no existence leak).

## Security

- Passwords: bcrypt (12 rounds). No plaintext ever.
- JWT HS256, 24h expiry, `Authorization: Bearer`.
- SlowAPI rate limits: register 5/min, login 10/min, requests 20/min.
- Role guards: donor endpoints require `donor` or `admin`; request creation requires `requester` or `admin`; admin-only endpoints (stats all, force-expire) require `admin`.
- Scoped queries: every query filters by `user_id` / `created_by` — foreign resources return 404.
- CORS allow-list from env. Secrets only via environment. Pydantic validation on every input.
- Input sanitization: strip whitespace, length caps on all string fields.

## Scaling Notes

- Indexes: `users(email)`, `blood_requests(status, city, blood_group)`, `offers(request_id)`, `blood_requests(request_number)`.
- Compat search is O(n) over donors in the same city (indexed by city) — trivially fast at this scale; at 100k+ donors, pre-filter with a `(blood_group, city)` composite index.
- Read-heavy public stats can be cached (Redis) at scale.
- Postgres + connection pooling (SQLAlchemy `pool_size`) in production; SQLite WAL for dev/self-host.
- Vercel serverless: stateless app, SQLite at `/tmp` per instance (ephemeral) — use Postgres for real multi-instance deployment.
