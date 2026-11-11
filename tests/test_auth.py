import hashlib

import pytest
from fakeredis import FakeAsyncRedis
from fastapi.testclient import TestClient
from redis.exceptions import ConnectionError

from backend.auth import COOKIE_NAME, PASSWORDS
from backend.config import Settings
from backend.main import create_app

ACCOUNT = {"email": "owner@example.com", "password": "correct-password-123", "name": "보호자"}


@pytest.fixture
def client(tmp_path):
    settings = Settings(_env_file=None, sqlite_path=str(tmp_path / "accounts.db"), auth_session_ttl_seconds=300)
    with TestClient(create_app(settings, redis_client=FakeAsyncRedis(decode_responses=True))) as client:
        yield client


def test_register_hashes_password_and_uses_httponly_redis_session(client):
    response = client.post("/api/v1/auth/register", json=ACCOUNT)
    assert response.status_code == 201
    user = response.json()["user"]
    assert set(user) == {"id", "email", "name"}
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie and "Path=/api/v1" in cookie
    assert "Max-Age=300" in cookie
    token = response.cookies[COOKIE_NAME]
    auth = client.app.state.auth
    keys = client.portal.call(auth.redis.keys, "meet-again:auth:session:*")
    assert keys == [auth.session_key(token)]
    assert token not in keys[0]
    assert hashlib.sha256(token.encode()).hexdigest() in keys[0]
    assert 0 < client.portal.call(auth.redis.ttl, keys[0]) <= 300
    account = client.portal.call(auth.store.get, auth.account_key(ACCOUNT["email"]), "identity", "account")
    assert account["password_hash"].startswith("$argon2")
    assert PASSWORDS.verify(ACCOUNT["password"], account["password_hash"])
    assert ACCOUNT["password"] not in str(account)
    assert client.get("/api/v1/auth/me").json()["user"] == user
    assert client.get("/api/v1/runs").headers["cache-control"] == "no-store"


def test_login_rotates_session_logout_revokes_it_and_old_demo_is_disabled(client):
    registration = client.post("/api/v1/auth/register", json=ACCOUNT)
    old_token = registration.cookies[COOKIE_NAME]
    response = client.post("/api/v1/auth/login", json={"email": "OWNER@example.com", "password": ACCOUNT["password"]})
    assert response.status_code == 200
    token = response.cookies[COOKIE_NAME]
    assert token != old_token
    assert client.get("/api/v1/auth/me", headers={"Cookie": f"{COOKIE_NAME}={old_token}"}).status_code == 401
    assert client.get("/api/v1/runs").status_code == 200
    assert client.post("/api/v1/auth/logout").status_code == 204
    assert client.get("/api/v1/auth/me", headers={"Cookie": f"{COOKIE_NAME}={token}"}).status_code == 401
    assert client.post("/api/v1/sessions").status_code == 404
    assert client.get("/api/v1/runs", headers={"Authorization": "Bearer " + "x" * 43}).status_code == 401


def test_expired_session_requires_login(client):
    response = client.post("/api/v1/auth/register", json=ACCOUNT)
    auth = client.app.state.auth
    client.portal.call(auth.redis.expire, auth.session_key(response.cookies[COOKIE_NAME]), -1)
    assert client.get("/api/v1/auth/me").status_code == 401


def test_login_failures_are_generic_and_limited_in_redis(client):
    client.post("/api/v1/auth/register", json=ACCOUNT)
    wrong = {"email": ACCOUNT["email"], "password": "incorrect-password"}
    first = client.post("/api/v1/auth/login", json=wrong)
    unknown = client.post("/api/v1/auth/login", json={**wrong, "email": "unknown@example.com"})
    assert first.status_code == unknown.status_code == 401
    assert first.json() == unknown.json()
    for _ in range(9):
        assert client.post("/api/v1/auth/login", json=wrong).status_code == 401
    limited = client.post("/api/v1/auth/login", json=wrong)
    assert limited.status_code == 429
    assert limited.headers["retry-after"] == "600"


def test_duplicate_account_and_input_validation(client):
    assert client.post("/api/v1/auth/register", json=ACCOUNT).status_code == 201
    assert client.post("/api/v1/auth/register", json={**ACCOUNT, "email": "OWNER@example.com"}).status_code == 409
    invalid = client.post("/api/v1/auth/register", json={**ACCOUNT, "password": "short"})
    assert invalid.status_code == 422
    assert "short" not in invalid.text and '"input"' not in invalid.text
    assert client.post("/api/v1/auth/register", json={**ACCOUNT, "name": "   "}).status_code == 422
    assert client.post("/api/v1/auth/login", json={"email": "invalid", "password": "test-password"}).status_code == 422


@pytest.mark.parametrize("origin", ["http://localhost:5173", "http://127.0.0.1:5173"])
def test_cookie_csrf_origin_and_credentialed_cors(client, origin):
    assert client.post("/api/v1/auth/register", json=ACCOUNT, headers={"Origin": "https://untrusted.example"}).status_code == 403
    response = client.post("/api/v1/auth/register", json=ACCOUNT, headers={"Origin": origin})
    assert response.status_code == 201
    assert response.headers["access-control-allow-origin"] == origin
    assert response.headers["access-control-allow-credentials"] == "true"
    assert client.post("/api/v1/auth/logout", headers={"Origin": "https://untrusted.example"}).status_code == 403
    assert client.get("/api/v1/auth/me").status_code == 200


def test_redis_outage_fails_closed(client, monkeypatch):
    client.post("/api/v1/auth/register", json=ACCOUNT)

    async def unavailable(*args, **kwargs):
        raise ConnectionError("test-only Redis failure")

    monkeypatch.setattr(client.app.state.auth.redis, "get", unavailable)
    assert client.get("/api/v1/runs").status_code == 503


def test_production_cookie_is_secure(tmp_path):
    settings = Settings(_env_file=None, sqlite_path=str(tmp_path / "secure.db"), auth_cookie_secure=True)
    with TestClient(create_app(settings, redis_client=FakeAsyncRedis(decode_responses=True)), base_url="https://testserver") as client:
        response = client.post("/api/v1/auth/register", json=ACCOUNT)
        assert response.status_code == 201 and "Secure" in response.headers["set-cookie"]
        assert client.get("/api/v1/auth/me").status_code == 200


def test_same_site_none_requires_secure_cookie():
    with pytest.raises(ValueError):
        Settings(_env_file=None, auth_cookie_samesite="none", auth_cookie_secure=False)
