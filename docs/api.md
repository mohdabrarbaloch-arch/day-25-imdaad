# API Reference

Base URL: `/api/v1` · Auth: `Authorization: Bearer <token>` (JWT, 24h)

Interactive docs at `/docs` (Swagger UI).

## Auth

### POST /auth/register — create account
```json
{ "email": "a@b.pk", "password": "password123", "full_name": "Ali", "phone": "03001234567", "role": "donor", "city": "Karachi" }
```
→ `201` `{ access_token, token_type, user }` · `409` duplicate email · `422` validation

### POST /auth/login
```json
{ "email": "a@b.pk", "password": "password123" }
```
→ `200` token+user · `401` bad credentials

### GET /auth/me — current user (auth)
→ `200` user object

## Donors

### POST /donors/profile (donor/admin)
```json
{ "blood_group": "O-", "last_donation_date": null, "is_available": true, "medical_notes": "" }
```
→ `201` donor profile · `409` duplicate · `422` invalid blood group

### GET /donors/me (auth)
→ `200` profile incl. computed `eligible` (available && >=56 days since last donation)

### PATCH /donors/me (auth)
Partial update: `{ "is_available": false }` etc.

### POST /donors/me/donate (donor/admin)
Records a donation → sets last_donation_date, increments count.

### GET /donors/search?blood_group=A-&city=Karachi&only_eligible=true (auth)
Returns donors **compatible with a recipient of `blood_group`**, filtered by city, eligible only by default.

## Blood Requests

### POST /requests (requester/admin)
```json
{ "patient_name": "Imran", "blood_group": "B+", "units": 2, "city": "Karachi", "hospital": "KGH", "urgency": "urgent", "note": "" }
```
→ `201` request with `request_number` (`IMD-2026-000001`) · expires after `REQUEST_EXPIRY_HOURS`

### GET /requests?status_filter=&city=&blood_group=&mine=true (auth)
Open requests by default; `mine=true` shows your own (all statuses).

### GET /requests/{id} (auth)
Owner/admin see any status; others only `open` (else 404).

### POST /requests/{id}/offers (donor/admin)
```json
{ "message": "I can donate" }
```
→ `201` offer · `409` duplicate/incompatible request state · `422` blood incompatible · `409` no donor profile

### GET /requests/{id}/offers (owner/admin)
Lists offers with donor name + blood group.

### POST /requests/{id}/fulfill (requester/admin)
`open`/`matched` → `fulfilled`; records donations for accepted donors. `409` otherwise.

### POST /requests/{id}/cancel (requester/admin)
`open`/`matched` → `cancelled`. `409` on terminal states.

### POST /requests/{id}/expire (admin)
`open` → `expired`.

## Offers

### PATCH /offers/{id}?action=accept|decline|withdraw (auth)
- `accept` / `decline`: request owner (or admin)
- `withdraw`: offer's donor (or admin)
- Only `pending` offers can change → `409` otherwise · `403` wrong actor

## Stats

### GET /stats (public)
```json
{ "total_donors": 5, "eligible_donors": 4, "open_requests": 2, "fulfilled_requests": 1,
  "total_requests": 4, "requests_by_blood_group": {...}, "donors_by_blood_group": {...} }
```

### GET /admin/stats (admin)
Users by role/city, requests by status.

## Error format

```json
{ "detail": "message" }
```
or for validation, `{ "detail": [ { "loc": [...], "msg": "...", "type": "..." } ] }`

## Status codes

| Code | Meaning |
|---|---|
| 200/201 | Success |
| 401 | Missing/invalid token |
| 403 | Wrong role or not your resource |
| 404 | Not found (also used to hide foreign resources) |
| 409 | State conflict (duplicate, illegal transition) |
| 422 | Validation / incompatible blood |
| 429 | Rate limited |
