"""Login, session cookie, health, Apple native nonce check."""

import hashlib

import pytest

pytestmark = pytest.mark.integration


async def test_health(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["db"] == "up"


async def test_login_sets_cookie_and_me_works(user_client):
    client, user = user_client
    resp = await client.get("/api/users/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == user.email


async def test_bad_password_is_refused(client, create_user):
    await create_user("bad@example.com", "correct-horse-battery")
    resp = await client.post(
        "/api/auth/login", data={"username": "bad@example.com", "password": "nope"}
    )
    assert resp.status_code == 400


async def test_anonymous_is_401(client):
    resp = await client.get("/api/users/me")
    assert resp.status_code == 401


async def test_providers_lists_apple(client):
    resp = await client.get("/api/auth/providers")
    assert resp.json() == {"apple": True}


def test_apple_nonce_accepts_raw_or_hashed():
    from app.auth.apple import nonce_matches

    raw = "abc123"
    assert nonce_matches(hashlib.sha256(raw.encode()).hexdigest(), raw)
    assert nonce_matches(raw, raw)
    assert not nonce_matches("other", raw)
    assert nonce_matches(None, None)
    assert not nonce_matches(None, raw)
