from __future__ import annotations

import hashlib
import hmac
from datetime import datetime
from typing import Any
from urllib.parse import urlencode

import httpx
from dateutil import parser as date_parser


class WhoopClient:
    auth_url = "https://api.prod.whoop.com/oauth/oauth2/auth"
    token_url = "https://api.prod.whoop.com/oauth/oauth2/token"
    base_url = "https://api.prod.whoop.com"

    def __init__(self, access_token: str | None = None):
        headers = {"Accept": "application/json"}
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        self.client = httpx.Client(base_url=self.base_url, headers=headers, timeout=30.0)

    def close(self) -> None:
        self.client.close()

    @classmethod
    def build_authorization_url(
        cls,
        *,
        client_id: str,
        redirect_uri: str,
        state: str,
        scopes: list[str],
    ) -> str:
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "state": state,
        }
        return f"{cls.auth_url}?{urlencode(params)}"

    @classmethod
    def exchange_code(
        cls,
        *,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        code: str,
    ) -> dict:
        response = httpx.post(
            cls.token_url,
            data={
                "grant_type": "authorization_code",
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "code": code,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()

    @classmethod
    def refresh_token(
        cls,
        *,
        client_id: str,
        client_secret: str,
        refresh_token: str,
    ) -> dict:
        response = httpx.post(
            cls.token_url,
            data={
                "grant_type": "refresh_token",
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()

    def get_profile(self) -> dict:
        return self._get("/developer/v2/user/profile/basic")

    def get_body_measurements(self) -> dict:
        return self._get("/developer/v2/user/measurement/body")

    def get_cycles(self, *, start: datetime, end: datetime, next_token: str | None = None) -> dict:
        return self._get_collection("/developer/v2/cycle", start=start, end=end, next_token=next_token)

    def get_recoveries(self, *, start: datetime, end: datetime, next_token: str | None = None) -> dict:
        return self._get_collection("/developer/v2/recovery", start=start, end=end, next_token=next_token)

    def get_sleeps(self, *, start: datetime, end: datetime, next_token: str | None = None) -> dict:
        return self._get_collection("/developer/v2/activity/sleep", start=start, end=end, next_token=next_token)

    def get_workouts(self, *, start: datetime, end: datetime, next_token: str | None = None) -> dict:
        return self._get_collection("/developer/v2/activity/workout", start=start, end=end, next_token=next_token)

    def get_sleep_by_id(self, sleep_id: str) -> dict:
        return self._get(f"/developer/v2/activity/sleep/{sleep_id}")

    def get_workout_by_id(self, workout_id: str) -> dict:
        return self._get(f"/developer/v2/activity/workout/{workout_id}")

    def get_recovery_for_cycle(self, cycle_id: str) -> dict:
        return self._get(f"/developer/v2/cycle/{cycle_id}/recovery")

    def revoke_access(self) -> None:
        response = self.client.delete("/developer/v2/user/access")
        response.raise_for_status()

    def _get_collection(
        self,
        path: str,
        *,
        start: datetime,
        end: datetime,
        next_token: str | None = None,
    ) -> dict:
        params: dict[str, Any] = {
            "limit": 25,
            "start": start.isoformat().replace("+00:00", "Z"),
            "end": end.isoformat().replace("+00:00", "Z"),
        }
        if next_token:
            params["nextToken"] = next_token
        return self._get(path, params=params)

    def _get(self, path: str, params: dict | None = None) -> dict:
        response = self.client.get(path, params=params)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def parse_datetime(value: str | None) -> datetime | None:
        if not value:
            return None
        return date_parser.isoparse(value)


def verify_whoop_signature(body: bytes, provided_signature: str | None, secret: str | None) -> bool:
    if not secret:
        return True
    if not provided_signature:
        return False
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    candidates = {
        digest,
        f"sha256={digest}",
    }
    return provided_signature in candidates

