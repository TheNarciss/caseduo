"""App Review demo account and the legal pages."""

import pytest

from app import demo

pytestmark = pytest.mark.integration


async def test_demo_account_has_a_living_history(client, db):
    await demo.refresh("demo@example.com", "demo-password-123")
    await demo.refresh("demo@example.com", "demo-password-456")  # rerunnable, new password
    resp = await client.post(
        "/api/auth/login", data={"username": "demo@example.com", "password": "demo-password-456"}
    )
    assert resp.status_code == 204
    today = (await client.get("/api/today")).json()
    assert today["cards"] and today["streak"]["current"] >= 3 and not today["easy_mode"]
    assert any(c["is_revenge"] for c in today["cards"])
    history = (await client.get("/api/history")).json()
    assert history["series"] and history["weaknesses"] and len(history["calendar"]) >= 6
    me = (await client.get("/api/me")).json()
    assert me["story_text"] and me["is_admin"] is False
    assert (await client.get("/api/league")).json()["members"]


async def test_legal_pages(client):
    for name in ("privacy.html", "about.html"):
        resp = await client.get(f"/legal/{name}")
        assert resp.status_code == 200 and "CaseDuo" in resp.text
    assert (await client.get("/legal/../main.py")).status_code == 404
