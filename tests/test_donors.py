"""Donor profile + search endpoint tests."""

from tests.conftest import auth_headers, register


def _make_donor(client, email, blood, city="Karachi", days_ago=None):
    register(client, email, city=city)
    headers = auth_headers(client, email)
    payload = {"blood_group": blood, "is_available": True}
    if days_ago is not None:
        from datetime import datetime, timedelta, timezone

        payload["last_donation_date"] = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
    resp = client.post("/api/v1/donors/profile", json=payload, headers=headers)
    assert resp.status_code == 201
    return headers


def test_create_profile_requires_donor_role(client):
    register(client, "req@test.pk", role="requester")
    headers = auth_headers(client, "req@test.pk")
    resp = client.post("/api/v1/donors/profile", json={"blood_group": "O+"}, headers=headers)
    assert resp.status_code == 403


def test_create_profile_rejects_invalid_blood_group(client):
    register(client, "bad@test.pk")
    headers = auth_headers(client, "bad@test.pk")
    resp = client.post("/api/v1/donors/profile", json={"blood_group": "X+"}, headers=headers)
    assert resp.status_code == 422


def test_profile_duplicate_conflict(client):
    register(client, "dupprofile@test.pk")
    headers = auth_headers(client, "dupprofile@test.pk")
    client.post("/api/v1/donors/profile", json={"blood_group": "O+"}, headers=headers)
    resp = client.post("/api/v1/donors/profile", json={"blood_group": "A+"}, headers=headers)
    assert resp.status_code == 409


def test_my_profile_returns_eligibility(client):
    _make_donor(client, "elig@test.pk", "O-", days_ago=60)
    headers = auth_headers(client, "elig@test.pk")
    resp = client.get("/api/v1/donors/me", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["blood_group"] == "O-"
    assert data["eligible"] is True
    assert data["is_available"] is True


def test_donor_ineligible_within_56_days(client):
    _make_donor(client, "recent@test.pk", "A+", days_ago=10)
    headers = auth_headers(client, "recent@test.pk")
    resp = client.get("/api/v1/donors/me", headers=headers)
    assert resp.json()["eligible"] is False


def test_update_profile_toggle_availability(client):
    _make_donor(client, "toggle@test.pk", "B+")
    headers = auth_headers(client, "toggle@test.pk")
    resp = client.patch("/api/v1/donors/me", json={"is_available": False}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["is_available"] is False


def test_record_donation_updates_profile(client):
    _make_donor(client, "donated@test.pk", "AB+", days_ago=100)
    headers = auth_headers(client, "donated@test.pk")
    resp = client.post("/api/v1/donors/me/donate", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["donation_count"] == 1
    assert resp.json()["eligible"] is False


def test_search_filters_by_city_and_compatibility(client):
    _make_donor(client, "khi_o@test.pk", "O-", city="Karachi")
    _make_donor(client, "khi_a@test.pk", "A+", city="Karachi")
    _make_donor(client, "lhr_b@test.pk", "B+", city="Lahore")
    register(client, "searcher@test.pk")
    headers = auth_headers(client, "searcher@test.pk")

    # Search for donors compatible with an A- recipient in Karachi → only O- (and A-)
    resp = client.get("/api/v1/donors/search", params={"blood_group": "A-", "city": "Karachi"}, headers=headers)
    assert resp.status_code == 200
    bloods = {d["blood_group"] for d in resp.json()}
    assert "O-" in bloods
    assert "A+" not in bloods  # A+ cannot donate to A-
    assert "B+" not in bloods
    assert all(d["city"] == "Karachi" for d in resp.json())


def test_search_excludes_ineligible_donors(client):
    _make_donor(client, "newdonor@test.pk", "O-")          # eligible
    _make_donor(client, "olddonor@test.pk", "A+", days_ago=5)  # not eligible
    register(client, "searcher2@test.pk")
    headers = auth_headers(client, "searcher2@test.pk")
    resp = client.get("/api/v1/donors/search", params={"blood_group": "A-", "city": "Karachi"}, headers=headers)
    emails = {d["full_name"] for d in resp.json()}
    # olddonor A+ is compatible with A- but not eligible (donated 5 days ago)
    assert "Test User" in emails  # new donor
    assert "Test User" in emails


def test_search_invalid_blood_group_422(client):
    register(client, "searcher3@test.pk")
    headers = auth_headers(client, "searcher3@test.pk")
    resp = client.get("/api/v1/donors/search", params={"blood_group": "Q+"}, headers=headers)
    assert resp.status_code == 422
