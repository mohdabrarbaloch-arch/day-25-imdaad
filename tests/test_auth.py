"""Auth endpoint tests."""

from app.models import User

from tests.conftest import auth_headers, register


def test_register_creates_donor(client):
    resp = register(client, "donor@test.pk")
    assert resp.status_code == 201
    data = resp.json()
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "donor@test.pk"
    assert data["user"]["role"] == "donor"
    assert "access_token" in data


def test_register_duplicate_email_conflict(client):
    register(client, "dup@test.pk")
    resp = register(client, "dup@test.pk")
    assert resp.status_code == 409


def test_register_rejects_weak_password(client):
    resp = register(client, "weak@test.pk", password="short")
    assert resp.status_code == 422


def test_register_rejects_invalid_role(client):
    resp = register(client, "badrole@test.pk", role="superuser")
    assert resp.status_code == 422


def test_login_success(client):
    register(client, "login@test.pk")
    resp = client.post("/api/v1/auth/login", json={"email": "login@test.pk", "password": "password123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_wrong_password(client):
    register(client, "wrongpw@test.pk")
    resp = client.post("/api/v1/auth/login", json={"email": "wrongpw@test.pk", "password": "nope-nope"})
    assert resp.status_code == 401


def test_login_unknown_email(client):
    resp = client.post("/api/v1/auth/login", json={"email": "ghost@test.pk", "password": "password123"})
    assert resp.status_code == 401


def test_me_requires_token(client):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_me_returns_user(client):
    register(client, "me@test.pk")
    headers = auth_headers(client, "me@test.pk")
    resp = client.get("/api/v1/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "me@test.pk"


def test_password_is_hashed_not_plaintext(client, db_session):
    register(client, "hash@test.pk")
    user = db_session.query(User).filter(User.email == "hash@test.pk").first()
    assert user is not None
    assert user.password_hash != "password123"
    assert user.password_hash.startswith("$2b$")
