"""Public stats endpoint tests."""

from tests.conftest import auth_headers, register


def test_public_stats_empty(client):
    resp = client.get("/api/v1/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_donors"] == 0
    assert data["open_requests"] == 0
    assert all(data["requests_by_blood_group"][g] == 0 for g in ["A+", "B+", "O+", "AB-", "O-"])


def test_public_stats_counts(client):
    # Donor
    register(client, "statdonor@test.pk")
    donor_headers = auth_headers(client, "statdonor@test.pk")
    client.post("/api/v1/donors/profile", json={"blood_group": "O-"}, headers=donor_headers)
    # Requester + request
    register(client, "statreq@test.pk", role="requester")
    req_headers = auth_headers(client, "statreq@test.pk")
    resp = client.post(
        "/api/v1/requests",
        json={"patient_name": "Patient", "blood_group": "B+", "units": 1, "city": "Karachi"},
        headers=req_headers,
    )
    assert resp.status_code == 201, resp.json()
    data = client.get("/api/v1/stats").json()
    assert data["total_donors"] == 1
    assert data["eligible_donors"] == 1
    assert data["open_requests"] == 1
    assert data["requests_by_blood_group"]["B+"] == 1
    assert data["donors_by_blood_group"]["O-"] == 1
