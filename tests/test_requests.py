"""Blood request lifecycle + offers tests."""

from tests.conftest import auth_headers, register


def _make_donor(client, email, blood, city="Karachi", days_ago=None):
    register(client, email, city=city)
    headers = auth_headers(client, email)
    payload = {"blood_group": blood, "is_available": True}
    if days_ago is not None:
        from datetime import datetime, timedelta, timezone

        payload["last_donation_date"] = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
    client.post("/api/v1/donors/profile", json=payload, headers=headers)
    return headers


def _make_requester(client, email="hospital@test.pk"):
    register(client, email, role="requester")
    return auth_headers(client, email)


def _create_request(client, headers, blood="B+", units=2, city="Karachi", urgency="urgent"):
    return client.post(
        "/api/v1/requests",
        json={
            "patient_name": "Test Patient",
            "blood_group": blood,
            "units": units,
            "city": city,
            "hospital": "Test Hospital",
            "urgency": urgency,
            "note": "Urgent need",
        },
        headers=headers,
    )


# ---------- Creation ----------
def test_create_request_requires_requester(client):
    register(client, "donoronly@test.pk")
    headers = auth_headers(client, "donoronly@test.pk")
    resp = _create_request(client, headers)
    assert resp.status_code == 403


def test_create_request_success(client):
    headers = _make_requester(client)
    resp = _create_request(client, headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["request_number"].startswith("IMD-")
    assert data["status"] == "open"
    assert data["offer_count"] == 0


def test_request_numbers_increment(client):
    headers = _make_requester(client)
    r1 = _create_request(client, headers).json()
    r2 = _create_request(client, headers).json()
    assert r1["request_number"] != r2["request_number"]


def test_create_request_rejects_bad_blood_group(client):
    headers = _make_requester(client)
    resp = _create_request(client, headers, blood="Z+")
    assert resp.status_code == 422


def test_create_request_rejects_bad_urgency(client):
    headers = _make_requester(client)
    resp = _create_request(client, headers, urgency="asap")
    assert resp.status_code == 422


def test_create_request_rejects_units_out_of_range(client):
    headers = _make_requester(client)
    resp = client.post(
        "/api/v1/requests",
        json={"patient_name": "X", "blood_group": "O+", "units": 0, "city": "Karachi", "urgency": "normal"},
        headers=headers,
    )
    assert resp.status_code == 422


# ---------- Listing & scoping ----------
def test_list_open_requests_only(client):
    req_headers = _make_requester(client)
    _create_request(client, req_headers)
    register(client, "viewer@test.pk")
    headers = auth_headers(client, "viewer@test.pk")
    resp = client.get("/api/v1/requests", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_list_mine_shows_own_closed_requests(client):
    headers = _make_requester(client)
    r = _create_request(client, headers).json()
    client.post(f"/api/v1/requests/{r['id']}/cancel", headers=headers)
    resp = client.get("/api/v1/requests", params={"mine": True}, headers=headers)
    assert len(resp.json()) == 1
    assert resp.json()[0]["status"] == "cancelled"


def test_get_foreign_non_open_request_is_404(client):
    req_headers = _make_requester(client)
    r = _create_request(client, req_headers).json()
    client.post(f"/api/v1/requests/{r['id']}/cancel", headers=req_headers)
    register(client, "stranger@test.pk")
    headers = auth_headers(client, "stranger@test.pk")
    resp = client.get(f"/api/v1/requests/{r['id']}", headers=headers)
    assert resp.status_code == 404


def test_get_open_request_visible_to_anyone(client):
    req_headers = _make_requester(client)
    r = _create_request(client, req_headers).json()
    register(client, "anon@test.pk")
    headers = auth_headers(client, "anon@test.pk")
    resp = client.get(f"/api/v1/requests/{r['id']}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "open"


# ---------- Offers ----------
def test_offer_flow_full_lifecycle(client):
    req_headers = _make_requester(client)
    r = _create_request(client, req_headers, blood="B+").json()
    donor_headers = _make_donor(client, "offerer@test.pk", "B+")

    resp = client.post(f"/api/v1/requests/{r['id']}/offers", json={"message": "I can donate"}, headers=donor_headers)
    assert resp.status_code == 201
    offer = resp.json()
    assert offer["status"] == "pending"
    assert offer["blood_group"] == "B+"

    resp = client.get(f"/api/v1/requests/{r['id']}/offers", headers=req_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = client.patch(f"/api/v1/offers/{offer['id']}", params={"action": "accept"}, headers=req_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "accepted"

    req = client.get(f"/api/v1/requests/{r['id']}", headers=req_headers).json()
    assert req["status"] == "matched"

    resp = client.post(f"/api/v1/requests/{r['id']}/fulfill", headers=req_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "fulfilled"


def test_offer_incompatible_blood_422(client):
    req_headers = _make_requester(client)
    r = _create_request(client, req_headers, blood="A-").json()
    donor_headers = _make_donor(client, "wrongblood@test.pk", "B+")
    resp = client.post(f"/api/v1/requests/{r['id']}/offers", json={"message": "can i help"}, headers=donor_headers)
    assert resp.status_code == 422


def test_duplicate_offer_conflict(client):
    req_headers = _make_requester(client)
    r = _create_request(client, req_headers, blood="O+").json()
    donor_headers = _make_donor(client, "twice@test.pk", "O+")
    client.post(f"/api/v1/requests/{r['id']}/offers", json={"message": "1"}, headers=donor_headers)
    resp = client.post(f"/api/v1/requests/{r['id']}/offers", json={"message": "2"}, headers=donor_headers)
    assert resp.status_code == 409


def test_offer_on_closed_request_conflict(client):
    req_headers = _make_requester(client)
    r = _create_request(client, req_headers).json()
    client.post(f"/api/v1/requests/{r['id']}/cancel", headers=req_headers)
    donor_headers = _make_donor(client, "late@test.pk", "O-")
    resp = client.post(f"/api/v1/requests/{r['id']}/offers", json={}, headers=donor_headers)
    assert resp.status_code == 409


def test_offer_requires_donor_profile(client):
    req_headers = _make_requester(client)
    r = _create_request(client, req_headers, blood="O+").json()
    register(client, "noprofile@test.pk")
    headers = auth_headers(client, "noprofile@test.pk")
    resp = client.post(f"/api/v1/requests/{r['id']}/offers", json={}, headers=headers)
    assert resp.status_code == 409


def test_offer_actions_permission_denied(client):
    req_headers = _make_requester(client)
    r = _create_request(client, req_headers, blood="AB+").json()
    donor_headers = _make_donor(client, "abdonor@test.pk", "AB+")
    offer = client.post(f"/api/v1/requests/{r['id']}/offers", json={}, headers=donor_headers).json()
    other_donor = _make_donor(client, "otherdonor@test.pk", "AB+")
    resp = client.patch(f"/api/v1/offers/{offer['id']}", params={"action": "accept"}, headers=other_donor)
    assert resp.status_code == 403


def test_offer_withdraw_by_donor(client):
    req_headers = _make_requester(client)
    r = _create_request(client, req_headers, blood="O+").json()
    donor_headers = _make_donor(client, "wdraw@test.pk", "O+")
    offer = client.post(f"/api/v1/requests/{r['id']}/offers", json={}, headers=donor_headers).json()
    resp = client.patch(f"/api/v1/offers/{offer['id']}", params={"action": "withdraw"}, headers=donor_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "withdrawn"


def test_accept_already_accepted_offer_conflict(client):
    req_headers = _make_requester(client)
    r = _create_request(client, req_headers, blood="A+").json()
    donor_headers = _make_donor(client, "again@test.pk", "A+")
    offer = client.post(f"/api/v1/requests/{r['id']}/offers", json={}, headers=donor_headers).json()
    client.patch(f"/api/v1/offers/{offer['id']}", params={"action": "accept"}, headers=req_headers)
    resp = client.patch(f"/api/v1/offers/{offer['id']}", params={"action": "withdraw"}, headers=donor_headers)
    assert resp.status_code == 409


# ---------- Request transitions ----------
def test_cancel_open_request(client):
    headers = _make_requester(client)
    r = _create_request(client, headers).json()
    resp = client.post(f"/api/v1/requests/{r['id']}/cancel", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


def test_cancel_fulfilled_request_conflict(client):
    req_headers = _make_requester(client)
    r = _create_request(client, req_headers, blood="O-").json()
    donor_headers = _make_donor(client, "fulfiller@test.pk", "O-")
    offer = client.post(f"/api/v1/requests/{r['id']}/offers", json={}, headers=donor_headers).json()
    client.patch(f"/api/v1/offers/{offer['id']}", params={"action": "accept"}, headers=req_headers)
    client.post(f"/api/v1/requests/{r['id']}/fulfill", headers=req_headers)
    resp = client.post(f"/api/v1/requests/{r['id']}/cancel", headers=req_headers)
    assert resp.status_code == 409


def test_fulfill_marks_accepted_donors_eligible_false(client):
    req_headers = _make_requester(client)
    r = _create_request(client, req_headers, blood="O+").json()
    donor_headers = _make_donor(client, "finaldonor@test.pk", "O+", days_ago=100)
    offer = client.post(f"/api/v1/requests/{r['id']}/offers", json={}, headers=donor_headers).json()
    client.patch(f"/api/v1/offers/{offer['id']}", params={"action": "accept"}, headers=req_headers)
    client.post(f"/api/v1/requests/{r['id']}/fulfill", headers=req_headers)
    me = client.get("/api/v1/donors/me", headers=donor_headers).json()
    assert me["donation_count"] == 1
    assert me["eligible"] is False


def test_expire_requires_admin(client):
    headers = _make_requester(client)
    r = _create_request(client, headers).json()
    resp = client.post(f"/api/v1/requests/{r['id']}/expire", headers=headers)
    assert resp.status_code == 403


def test_expire_by_admin(client):
    register(client, "admin@test.pk", role="admin")
    admin_headers = auth_headers(client, "admin@test.pk")
    req_headers = _make_requester(client)
    r = _create_request(client, req_headers).json()
    resp = client.post(f"/api/v1/requests/{r['id']}/expire", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "expired"


def test_foreign_request_404_for_requester(client):
    other_headers = _make_requester(client, email="otherhospital@test.pk")
    r = _create_request(client, other_headers).json()
    client.post(f"/api/v1/requests/{r['id']}/cancel", headers=other_headers)
    headers = _make_requester(client, email="another@test.pk")
    resp = client.post(f"/api/v1/requests/{r['id']}/cancel", headers=headers)
    assert resp.status_code == 404


def test_requests_list_status_filter(client):
    req_headers = _make_requester(client)
    r = _create_request(client, req_headers).json()
    client.post(f"/api/v1/requests/{r['id']}/cancel", headers=req_headers)
    resp = client.get("/api/v1/requests", params={"status_filter": "cancelled", "mine": True}, headers=req_headers)
    assert len(resp.json()) == 1
    assert resp.json()[0]["status"] == "cancelled"
