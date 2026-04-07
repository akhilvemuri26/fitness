from __future__ import annotations

from datetime import datetime

import httpx
from dateutil import parser as date_parser


class HevyClient:
    base_url = "https://api.hevyapp.com/v1"

    def __init__(self, api_key: str):
        self.client = httpx.Client(
            base_url=self.base_url,
            headers={"api-key": api_key},
            timeout=30.0,
        )

    def close(self) -> None:
        self.client.close()

    def get_user_info(self) -> dict:
        return self._get("/user/info")

    def get_workouts_page(self, page: int, page_size: int = 10) -> dict:
        return self._get("/workouts", params={"page": page, "pageSize": page_size})

    def get_workout_events(self, since: datetime, page: int, page_size: int = 10) -> dict:
        return self._get(
            "/workouts/events",
            params={
                "page": page,
                "pageSize": page_size,
                "since": since.isoformat().replace("+00:00", "Z"),
            },
        )

    def get_exercise_templates_page(self, page: int, page_size: int = 100) -> dict:
        return self._get(
            "/exercise_templates",
            params={"page": page, "pageSize": page_size},
        )

    def _get(self, path: str, params: dict | None = None) -> dict:
        response = self.client.get(path, params=params)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def parse_datetime(value: str | None) -> datetime | None:
        if not value:
            return None
        return date_parser.isoparse(value)

