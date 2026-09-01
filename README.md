# 🩸 Imdaad (امداد) — Blood Donation Network for Pakistan

Every day in Pakistan, someone posts on Facebook or WhatsApp: *"Emergency — need B+ blood in Karachi."* Then starts the frantic chain of calls, forwards, and crossed fingers. **Imdaad** replaces that chaos with a simple platform: hospitals and families post blood requests, verified donors register their blood group, and a real **ABO/Rh compatibility engine** instantly shows who can help.

> امداد — Urdu for "help, aid, assistance". That's the whole point.

## ✨ Features

- 🩸 **Real blood compatibility engine** — full ABO + Rh rules, universal donor (O-) and universal recipient (AB+) handled correctly
- 📢 **Urgent blood requests** — hospitals/families post with patient name, blood group, units, city, hospital, urgency level
- 🤝 **Donor offers** — donors offer blood on open requests; requesters accept/decline; request auto-locks when matched
- ✅ **Eligibility tracking** — 56-day donation cooldown, availability toggle, donation history
- 🔎 **Donor search** — find compatible donors by city and blood group, eligible-only filter
- 📊 **Live stats** — total/eligible donors, open/fulfilled requests, breakdowns by blood group
- 🏷️ **Request numbers** — `IMD-2026-000001` style, unique per year
- 🕒 **Auto-expiry** — open requests expire after 72h (configurable)
- 🔐 **Secure** — JWT + bcrypt(12), rate limiting, role-based access (donor/requester/admin), scoped queries (foreign access → 404)
- 📱 **Mobile-first dark SPA** — zero build step, works on the cheapest Android phone

## 🧱 Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI 0.115 · Python 3.11 · SQLAlchemy 2.0 · Pydantic v2 |
| Auth | JWT (HS256, 24h) · bcrypt (12 rounds) · SlowAPI rate limits |
| Database | SQLite (dev, WAL) · PostgreSQL 16 (docker-compose) |
| Frontend | Vanilla JS · mobile-first dark SPA · zero build step |
| Infra | Docker · docker-compose · Vercel-ready |

## 🚀 Quick Start

### Option A — Docker (recommended)

```bash
docker compose up --build
# API → http://localhost:8000  ·  Docs → http://localhost:8000/docs
```

### Option B — Local

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python seed.py                    # demo data + accounts
uvicorn app.main:app --reload     # → http://localhost:8000
```

### Option C — Vercel

Repo includes `vercel.json` + `api/index.py` — import the repo in Vercel, set `SECRET_KEY` (and `DATABASE_URL` to Postgres for persistence), deploy. Zero-config build (Python).

## 🔑 Demo Accounts (after `python seed.py`)

| Email | Password | Role |
|---|---|---|
| `admin@imdaad.pk` | `password123` | admin |
| `ahmed@imdaad.pk` | `password123` | donor (O-) |
| `hospital@imdaad.pk` | `password123` | requester |

## 🧪 Testing

```bash
pip install -r requirements.txt pytest
python -m pytest tests/ -q    # 60 tests: compatibility, auth, donors, requests, offers, stats
```

## 🏗️ Project Structure

```
app/
  main.py          # FastAPI entrypoint
  config.py        # env-driven settings
  database.py      # engine + session
  models.py        # ORM: User, DonorProfile, BloodRequest, Offer
  schemas.py       # Pydantic v2 schemas
  security.py      # bcrypt + JWT + role guards
  compat.py        # ABO/Rh compatibility engine (pure functions)
  routers/
    auth.py        # register / login / me
    donors.py      # profiles, eligibility, search
    requests.py    # request lifecycle + offers
    offers.py      # accept / decline / withdraw
    stats.py       # public + admin stats
static/            # mobile-first SPA (index.html, styles.css, app.js)
tests/             # 60 unit + API tests
docs/              # setup, usage, API reference
seed.py            # demo data
```

## 🩸 Compatibility Matrix

| Donor \ Recipient | A+ | A- | B+ | B- | AB+ | AB- | O+ | O- |
|---|---|---|---|---|---|---|---|---|
| **A+** | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **A-** | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ |
| **B+** | ❌ | ❌ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **B-** | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| **AB+** | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **AB-** | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ |
| **O+** | ✅ | ❌ | ✅ | ❌ | ✅ | ❌ | ✅ | ❌ |
| **O-** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

**O-** = universal donor · **AB+** = universal recipient

## 📚 Docs

- [Setup Guide](docs/setup.md)
- [Usage Guide](docs/usage.md)
- [API Reference](docs/api.md)
- [Architecture](ARCHITECTURE.md)

## 📄 License

MIT — see [LICENSE](LICENSE).

---

*Built as Day 25 of the 30-Day Autonomous AI Software Engineer Challenge. One production-ready project per day.*
