"""Minimal APNs client: HTTP/2 with httpx, token-based auth (JWT ES256 with the .p8 key).

The same key format and signing as Tangent's Sign in with Apple
(`APPLE_PRIVATE_KEY_B64`): APNS_PRIVATE_KEY_B64 is the .p8 file in base64.
One key serves every app of the developer account.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any

import httpx
import jwt

logger = logging.getLogger(__name__)

HOSTS = {
    "production": "https://api.push.apple.com",
    "sandbox": "https://api.sandbox.push.apple.com",
}
TOKEN_REFRESH_SECONDS = 50 * 60  # Apple: valid 1 h, refresh no more than every 20 min

TEAM_ID = os.getenv("APNS_TEAM_ID", "")
KEY_ID = os.getenv("APNS_KEY_ID", "")
PRIVATE_KEY_B64 = os.getenv("APNS_PRIVATE_KEY_B64", "")
BUNDLE_ID = os.getenv("APNS_BUNDLE_ID", "uk.riskybusinesses.caseduo")

_token: tuple[str, float] | None = None


def is_configured() -> bool:
    return bool(TEAM_ID and KEY_ID and PRIVATE_KEY_B64)


def provider_token(*, now: float | None = None) -> str:
    global _token
    now = now if now is not None else time.time()
    if _token and now - _token[1] < TOKEN_REFRESH_SECONDS:
        return _token[0]
    key = base64.b64decode(PRIVATE_KEY_B64).decode()
    token = jwt.encode(
        {"iss": TEAM_ID, "iat": int(now)}, key, algorithm="ES256", headers={"kid": KEY_ID}
    )
    _token = (token, now)
    return token


def payload(title: str, body: str, *, badge: int | None = None) -> dict[str, Any]:
    aps: dict[str, Any] = {"alert": {"title": title, "body": body}, "sound": "default"}
    if badge is not None:
        aps["badge"] = max(0, badge)
    return {"aps": aps}


@dataclass
class SendResult:
    ok: bool
    status: int
    reason: str | None = None

    @property
    def token_invalid(self) -> bool:
        """The device token is dead: forget it."""
        return self.status == 410 or self.reason in ("BadDeviceToken", "Unregistered")


async def send(
    device_token: str,
    title: str,
    body: str,
    *,
    environment: str | None = "production",
    badge: int | None = None,
    collapse_id: str | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> SendResult:
    if not is_configured():
        return SendResult(ok=False, status=0, reason="not_configured")
    host = HOSTS.get(environment or "production", HOSTS["production"])
    headers = {
        "authorization": f"bearer {provider_token()}",
        "apns-topic": BUNDLE_ID,
        "apns-push-type": "alert",
        "apns-priority": "10",
    }
    if collapse_id:
        headers["apns-collapse-id"] = collapse_id
    async with httpx.AsyncClient(
        http2=transport is None, transport=transport, timeout=10
    ) as client:
        try:
            resp = await client.post(
                f"{host}/3/device/{device_token}",
                headers=headers,
                content=json.dumps(payload(title, body, badge=badge)),
            )
        except httpx.HTTPError as exc:
            logger.warning("APNs unreachable: %s", exc)
            return SendResult(ok=False, status=0, reason="network")
    reason = None
    if resp.status_code != 200:
        try:
            reason = resp.json().get("reason")
        except ValueError:
            reason = resp.text[:100]
        logger.warning("APNs refused a push: %s %s", resp.status_code, reason)
    return SendResult(ok=resp.status_code == 200, status=resp.status_code, reason=reason)
