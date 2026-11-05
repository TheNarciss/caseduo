"""Push decisions and the APNs client (mocked transport)."""

import base64
import json
from datetime import date, datetime
from zoneinfo import ZoneInfo

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from app.push import apns
from app.push.rules import PushState, decide

SG = ZoneInfo("Asia/Singapore")


def state(**kw):
    base = dict(
        notifications_enabled=True,
        has_token=True,
        disengaged=False,
        last_push_date=None,
        last_active_date=date(2026, 11, 3),
        streak_current=4,
        goal_met_today=False,
    )
    base.update(kw)
    return PushState(**base)


def at(h, m, d=4):
    return datetime(2026, 11, d, h, m, tzinfo=SG)


def test_streak_saver_at_20_local_only():
    push = decide(state(), at(20, 5))
    assert push.kind == "streak_saver"
    assert push.body == "Ta série de 4 jours se termine dans 4 h"
    assert decide(state(), at(19, 59)) is None
    assert decide(state(), at(20, 15)) is None
    assert decide(state(streak_current=1), at(20, 0)).body.startswith("Ta série de 1 jour ")


def test_no_push_when_goal_met_or_already_pushed_or_off():
    assert decide(state(goal_met_today=True), at(20, 0)) is None
    assert decide(state(last_push_date=date(2026, 11, 4)), at(20, 0)) is None
    assert decide(state(notifications_enabled=False), at(20, 0)) is None
    assert decide(state(has_token=False), at(20, 0)) is None
    assert decide(state(streak_current=0), at(20, 0)) is None


def test_disengagement_after_seven_days_then_silence():
    push = decide(state(last_active_date=date(2026, 10, 28)), at(20, 0))
    assert push.kind == "disengage"
    assert push.body == "On arrête les rappels pour l'instant. Reviens quand tu veux."
    assert decide(state(last_active_date=date(2026, 10, 28), disengaged=True), at(20, 0)) is None


@pytest.fixture
def apns_key(monkeypatch):
    key = ec.generate_private_key(ec.SECP256R1())
    pem = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    )
    monkeypatch.setattr(apns, "TEAM_ID", "TEAM123456")
    monkeypatch.setattr(apns, "KEY_ID", "KEY1234567")
    monkeypatch.setattr(apns, "PRIVATE_KEY_B64", base64.b64encode(pem).decode())
    monkeypatch.setattr(apns, "_token", None)
    return key


def test_provider_token_is_es256_and_cached(apns_key):
    token = apns.provider_token(now=1000.0)
    header = jwt.get_unverified_header(token)
    assert header == {"alg": "ES256", "kid": "KEY1234567", "typ": "JWT"}
    claims = jwt.decode(token, apns_key.public_key(), algorithms=["ES256"])
    assert claims == {"iss": "TEAM123456", "iat": 1000}
    assert apns.provider_token(now=1000.0 + 60) == token
    assert apns.provider_token(now=1000.0 + 3600) != token


async def test_send_builds_the_request_and_reads_errors(apns_key):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["headers"] = dict(request.headers)
        seen["body"] = json.loads(request.content)
        if request.url.path.endswith("dead"):
            return httpx.Response(410, json={"reason": "Unregistered"})
        return httpx.Response(200)

    transport = httpx.MockTransport(handler)
    ok = await apns.send(
        "abcd",
        "CaseDuo",
        "Hello",
        environment="sandbox",
        badge=3,
        collapse_id="x",
        transport=transport,
    )
    assert ok.ok and seen["url"] == "https://api.sandbox.push.apple.com/3/device/abcd"
    assert seen["headers"]["apns-topic"] == apns.BUNDLE_ID
    assert seen["headers"]["apns-push-type"] == "alert"
    assert seen["body"] == {
        "aps": {"alert": {"title": "CaseDuo", "body": "Hello"}, "sound": "default", "badge": 3}
    }
    dead = await apns.send("dead", "t", "b", transport=transport)
    assert not dead.ok and dead.token_invalid


async def test_send_without_configuration(monkeypatch):
    monkeypatch.setattr(apns, "TEAM_ID", "")
    assert (await apns.send("x", "t", "b")).reason == "not_configured"
