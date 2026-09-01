# Usage Guide

## Roles

| Role | Can do |
|---|---|
| **donor** | Create donor profile (blood group), toggle availability, record donations, search compatible donors, offer blood on open requests, withdraw own offers |
| **requester** | Post blood requests, view offers on own requests, accept/decline offers, mark requests fulfilled/cancelled |
| **admin** | Everything above + force-expire requests, admin stats |

## Donor flow

1. Register with role **donor**.
2. Create your donor profile: pick your blood group, mark yourself available.
3. Browse open requests on the dashboard and click **Offer to donate** on any you can help with.
4. When you actually donate, click **Record a donation** — the 56-day cooldown starts automatically.
5. Keep your availability toggle honest: flip it off when you can't donate.

## Requester flow

1. Register with role **requester** (e.g. hospital account or patient family).
2. Post a blood request: patient name, blood group, units, city, hospital, urgency.
3. Donors see your request and send offers.
4. Review offers on **My requests** → accept the best one (request locks as `matched`) or decline.
5. After donation, click **Mark fulfilled** — accepted donors get their donation recorded automatically.
6. Cancel anytime while the request is `open` or `matched`.

## Compatibility

Open the landing page and click any blood group in **"Who can donate to whom?"** — the app shows every compatible donor group instantly. Rules:

- **O-** can donate to everyone (universal donor).
- **AB+** can receive from everyone (universal recipient).
- Rh-negative can donate to Rh-positive of the same ABO; never the reverse.

## Public tracking

- `/api/v1/stats` — public, no auth: donor counts, open/fulfilled requests, per-group breakdowns.
- Open requests are visible to any logged-in user; closed requests are only visible to their owner or an admin (404 otherwise — no information leak).

## Seed data

`python seed.py` creates demo users (see README) and two sample requests with one offer.
