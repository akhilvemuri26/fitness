from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.derived import LinkedWorkoutSession
from app.models.hevy import HevyExerciseTemplate, HevyWorkout, HevyWorkoutExercise, HevyWorkoutSet
from app.models.source import SourceAccount, SourceStatus, SourceType
from app.models.whoop import (
    WhoopBodyMeasurement,
    WhoopCycle,
    WhoopRecovery,
    WhoopSleep,
    WhoopWorkout,
)
from app.services.connectors.hevy import HevyClient
from app.services.connectors.whoop import WhoopClient
from app.services.matching import MatchCandidate, WorkoutMatcher
from app.services.source_accounts import SourceAccountService


class HevySyncService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.source_service = SourceAccountService(db)
        self.local_tz = ZoneInfo(self.settings.canonical_timezone)

    def sync(self, backfill_days: int | None = None) -> dict:
        if not self.settings.hevy_api_key:
            raise ValueError("HEVY_API_KEY is not configured")

        account = self.source_service.get_or_create(SourceType.HEVY, "Hevy")
        client = HevyClient(self.settings.hevy_api_key)
        now = datetime.now(UTC)
        try:
            info = client.get_user_info()
            account.external_user_id = str(info.get("id") or info.get("user_id") or "")
            account.profile_json = info
            self._sync_templates(account, client)

            cursor = self.source_service.get_cursor(account, "workouts_events_since")
            if cursor and cursor.cursor_value:
                self._sync_workout_events(account, client, datetime.fromisoformat(cursor.cursor_value))
            else:
                self._backfill_workouts(account, client, backfill_days or self.settings.default_backfill_days)

            self._link_workouts()
            self.source_service.set_status(
                account,
                status=SourceStatus.CONNECTED,
                last_synced_at=now,
                last_error=None,
            )
            self.source_service.set_cursor(account, "workouts_events_since", now.isoformat())
            self.db.commit()
            return {"status": "ok", "source": "hevy", "synced_at": now.isoformat()}
        except Exception as exc:
            self.source_service.set_status(account, status=SourceStatus.ERROR, last_error=str(exc))
            self.db.commit()
            raise
        finally:
            client.close()

    def _sync_templates(self, account: SourceAccount, client: HevyClient) -> None:
        page = 1
        while True:
            response = client.get_exercise_templates_page(page=page)
            for item in response.get("exercise_templates", []):
                existing = self.db.scalar(
                    select(HevyExerciseTemplate).where(HevyExerciseTemplate.external_id == item["id"])
                )
                if existing is None:
                    existing = HevyExerciseTemplate(
                        source_account_id=account.id,
                        external_id=item["id"],
                        title=item["title"],
                        raw_payload=item,
                    )
                    self.db.add(existing)
                existing.title = item["title"]
                existing.exercise_type = item.get("type")
                existing.primary_muscle_group = item.get("primary_muscle_group")
                existing.secondary_muscle_groups_json = item.get("secondary_muscle_groups")
                existing.is_custom = bool(item.get("is_custom", False))
                existing.raw_payload = item
            if page >= response.get("page_count", 1):
                break
            page += 1

    def _backfill_workouts(self, account: SourceAccount, client: HevyClient, backfill_days: int) -> None:
        cutoff = datetime.now(self.local_tz).date() - timedelta(days=backfill_days)
        page = 1
        while True:
            response = client.get_workouts_page(page=page)
            for item in response.get("workouts", []):
                started_at = HevyClient.parse_datetime(item.get("start_time"))
                if started_at and started_at.astimezone(self.local_tz).date() < cutoff:
                    continue
                self._upsert_workout(account, item)
            if page >= response.get("page_count", 1):
                break
            page += 1

    def _sync_workout_events(self, account: SourceAccount, client: HevyClient, since: datetime) -> None:
        page = 1
        while True:
            response = client.get_workout_events(since=since, page=page)
            for event in response.get("events", []):
                if event["type"] == "updated":
                    self._upsert_workout(account, event["workout"])
                elif event["type"] == "deleted":
                    self._mark_workout_deleted(event["id"], event.get("deleted_at"))
            if page >= response.get("page_count", 1):
                break
            page += 1

    def _mark_workout_deleted(self, external_id: str, deleted_at: str | None) -> None:
        workout = self.db.scalar(select(HevyWorkout).where(HevyWorkout.external_id == external_id))
        if workout:
            workout.is_deleted = True
            if deleted_at:
                workout.updated_at_remote = datetime.fromisoformat(deleted_at.replace("Z", "+00:00"))

    def _upsert_workout(self, account: SourceAccount, payload: dict) -> None:
        workout = self.db.scalar(select(HevyWorkout).where(HevyWorkout.external_id == payload["id"]))
        if workout is None:
            workout = HevyWorkout(
                source_account_id=account.id,
                external_id=payload["id"],
                title=payload.get("title") or "Untitled Workout",
                started_at=HevyClient.parse_datetime(payload["start_time"]) or datetime.now(UTC),
                raw_payload=payload,
            )
            self.db.add(workout)
            self.db.flush()

        workout.title = payload.get("title") or "Untitled Workout"
        workout.description = payload.get("description")
        workout.routine_id = payload.get("routine_id")
        workout.started_at = HevyClient.parse_datetime(payload.get("start_time")) or workout.started_at
        workout.ended_at = HevyClient.parse_datetime(payload.get("end_time"))
        workout.created_at_remote = HevyClient.parse_datetime(payload.get("created_at"))
        workout.updated_at_remote = HevyClient.parse_datetime(payload.get("updated_at"))
        workout.local_date = workout.started_at.astimezone(self.local_tz).date()
        workout.is_deleted = False
        workout.raw_payload = payload

        self.db.execute(delete(HevyWorkoutSet).where(HevyWorkoutSet.exercise_id.in_(
            select(HevyWorkoutExercise.id).where(HevyWorkoutExercise.workout_id == workout.id)
        )))
        self.db.execute(delete(HevyWorkoutExercise).where(HevyWorkoutExercise.workout_id == workout.id))
        self.db.flush()

        for exercise in payload.get("exercises", []):
            exercise_row = HevyWorkoutExercise(
                workout_id=workout.id,
                exercise_index=int(exercise.get("index", 0)),
                title=exercise.get("title") or "Exercise",
                notes=exercise.get("notes"),
                exercise_template_id=exercise.get("exercise_template_id"),
                superset_id=exercise.get("supersets_id"),
            )
            self.db.add(exercise_row)
            self.db.flush()
            for set_payload in exercise.get("sets", []):
                self.db.add(
                    HevyWorkoutSet(
                        exercise_id=exercise_row.id,
                        set_index=int(set_payload.get("index", 0)),
                        set_type=set_payload.get("type"),
                        weight_kg=set_payload.get("weight_kg"),
                        reps=set_payload.get("reps"),
                        distance_meters=set_payload.get("distance_meters"),
                        duration_seconds=set_payload.get("duration_seconds"),
                        rpe=set_payload.get("rpe"),
                        custom_metric=set_payload.get("custom_metric"),
                    )
                )

    def _link_workouts(self) -> None:
        matcher = WorkoutMatcher()
        hevy_workouts = self.db.scalars(
            select(HevyWorkout).where(HevyWorkout.is_deleted.is_(False)).order_by(HevyWorkout.started_at.asc())
        ).all()
        for workout in hevy_workouts:
            existing_link = self.db.scalar(
                select(LinkedWorkoutSession).where(LinkedWorkoutSession.hevy_workout_id == workout.id)
            )
            if existing_link:
                continue
            candidates = self.db.scalars(
                select(WhoopWorkout).where(
                    WhoopWorkout.local_date == workout.local_date,
                    WhoopWorkout.deleted_at.is_(None),
                )
            ).all()
            result = matcher.match(
                MatchCandidate(id=workout.id, started_at=workout.started_at, ended_at=workout.ended_at),
                [
                    MatchCandidate(id=candidate.id, started_at=candidate.started_at, ended_at=candidate.ended_at)
                    for candidate in candidates
                ],
            )
            if result.target_id:
                self.db.add(
                    LinkedWorkoutSession(
                        hevy_workout_id=workout.id,
                        whoop_workout_id=result.target_id,
                        match_confidence=result.confidence,
                        match_reason=result.reason,
                        linked_at=datetime.now(UTC),
                    )
                )


class WhoopSyncService:
    scopes = [
        "offline",
        "read:profile",
        "read:body_measurement",
        "read:cycles",
        "read:recovery",
        "read:sleep",
        "read:workout",
    ]

    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.source_service = SourceAccountService(db)
        self.local_tz = ZoneInfo(self.settings.canonical_timezone)

    def build_authorization_url(self, state: str) -> str:
        if not all(
            [
                self.settings.whoop_client_id,
                self.settings.whoop_redirect_uri,
            ]
        ):
            raise ValueError("WHOOP OAuth configuration is incomplete")
        return WhoopClient.build_authorization_url(
            client_id=self.settings.whoop_client_id,
            redirect_uri=self.settings.whoop_redirect_uri,
            state=state,
            scopes=self.scopes,
        )

    def connect_with_code(self, code: str) -> SourceAccount:
        if not all(
            [
                self.settings.whoop_client_id,
                self.settings.whoop_client_secret,
                self.settings.whoop_redirect_uri,
            ]
        ):
            raise ValueError("WHOOP OAuth configuration is incomplete")

        token_response = WhoopClient.exchange_code(
            client_id=self.settings.whoop_client_id,
            client_secret=self.settings.whoop_client_secret,
            redirect_uri=self.settings.whoop_redirect_uri,
            code=code,
        )
        account = self.source_service.get_or_create(SourceType.WHOOP, "WHOOP")
        self._apply_token_response(account, token_response)

        client = WhoopClient(account.access_token)
        try:
            profile = client.get_profile()
            account.external_user_id = str(profile.get("user_id") or profile.get("id") or "")
            account.profile_json = profile
            self.source_service.set_status(account, status=SourceStatus.CONNECTED)
            self.db.commit()
            return account
        finally:
            client.close()

    def reconcile(self, backfill_days: int | None = None) -> dict:
        account = self.source_service.get(SourceType.WHOOP)
        if account is None or not account.refresh_token:
            raise ValueError("WHOOP account is not connected")

        self._refresh_if_needed(account)
        client = WhoopClient(account.access_token)
        now = datetime.now(UTC)
        cursor = self.source_service.get_cursor(account, "collections_since")
        start = (
            datetime.fromisoformat(cursor.cursor_value)
            if cursor and cursor.cursor_value
            else now - timedelta(days=backfill_days or self.settings.default_backfill_days)
        )
        try:
            account.profile_json = client.get_profile()
            body = client.get_body_measurements()
            self._upsert_body_measurement(account, body)
            self._paginate_and_store(account, client.get_cycles, self._upsert_cycle, start, now)
            self._paginate_and_store(account, client.get_recoveries, self._upsert_recovery, start, now)
            self._paginate_and_store(account, client.get_sleeps, self._upsert_sleep, start, now)
            self._paginate_and_store(account, client.get_workouts, self._upsert_workout, start, now)

            self.source_service.set_status(
                account,
                status=SourceStatus.CONNECTED,
                last_error=None,
                last_synced_at=now,
            )
            self.source_service.set_cursor(account, "collections_since", now.isoformat())
            self.db.commit()
            return {"status": "ok", "source": "whoop", "synced_at": now.isoformat()}
        except Exception as exc:
            self.source_service.set_status(account, status=SourceStatus.ERROR, last_error=str(exc))
            self.db.commit()
            raise
        finally:
            client.close()

    def process_webhook(self, payload: dict) -> None:
        account = self.source_service.get(SourceType.WHOOP)
        if account is None:
            return
        self.source_service.record_raw_event(
            source_type=SourceType.WHOOP,
            event_type=payload.get("type", "unknown"),
            external_id=str(payload.get("id")) if payload.get("id") is not None else None,
            payload=payload,
        )
        self.db.commit()

        event_type = payload.get("type", "")
        record_id = str(payload.get("id")) if payload.get("id") is not None else None
        if not record_id:
            return

        self._refresh_if_needed(account)
        client = WhoopClient(account.access_token)
        try:
            if event_type == "workout.deleted":
                row = self.db.scalar(select(WhoopWorkout).where(WhoopWorkout.external_id == record_id))
                if row:
                    row.deleted_at = datetime.now(UTC)
            elif event_type == "workout.updated":
                self._upsert_workout(account, client.get_workout_by_id(record_id))
            elif event_type == "sleep.updated":
                self._upsert_sleep(account, client.get_sleep_by_id(record_id))
            elif event_type == "recovery.updated":
                self._upsert_recovery(account, client.get_recovery_for_cycle(record_id))
            account.last_synced_at = datetime.now(UTC)
            self.db.commit()
        finally:
            client.close()

    def _refresh_if_needed(self, account: SourceAccount) -> None:
        expires_at = self._normalize_utc(account.token_expires_at)
        should_refresh = expires_at is None or expires_at <= datetime.now(UTC) + timedelta(minutes=5)
        if not should_refresh:
            return
        if not all([self.settings.whoop_client_id, self.settings.whoop_client_secret, account.refresh_token]):
            raise ValueError("WHOOP refresh token configuration is incomplete")
        token_response = WhoopClient.refresh_token(
            client_id=self.settings.whoop_client_id,
            client_secret=self.settings.whoop_client_secret,
            refresh_token=account.refresh_token,
        )
        self._apply_token_response(account, token_response)
        self.db.commit()

    def _apply_token_response(self, account: SourceAccount, token_response: dict) -> None:
        expires_in = int(token_response.get("expires_in", 3600))
        account.access_token = token_response["access_token"]
        account.refresh_token = token_response.get("refresh_token")
        account.token_expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)
        account.credentials_json = {
            **(account.credentials_json or {}),
            "scope": token_response.get("scope"),
            "token_type": token_response.get("token_type", "bearer"),
        }

    def _paginate_and_store(self, account: SourceAccount, fetcher, upsert_fn, start: datetime, end: datetime) -> None:
        next_token = None
        while True:
            page = fetcher(start=start, end=end, next_token=next_token)
            for record in page.get("records", []):
                upsert_fn(account, record)
            next_token = page.get("next_token")
            if not next_token:
                break

    def _upsert_cycle(self, account: SourceAccount, payload: dict) -> None:
        row = self.db.scalar(select(WhoopCycle).where(WhoopCycle.external_id == str(payload["id"])))
        if row is None:
            row = WhoopCycle(
                source_account_id=account.id,
                external_id=str(payload["id"]),
                started_at=WhoopClient.parse_datetime(payload["start"]) or datetime.now(UTC),
                raw_payload=payload,
            )
            self.db.add(row)
        row.started_at = WhoopClient.parse_datetime(payload.get("start")) or row.started_at
        row.ended_at = WhoopClient.parse_datetime(payload.get("end"))
        row.local_date = row.started_at.astimezone(self.local_tz).date()
        row.timezone_offset = payload.get("timezone_offset")
        row.score_state = payload.get("score_state")
        score = payload.get("score") or {}
        row.strain = score.get("strain")
        row.kilojoule = score.get("kilojoule")
        row.average_heart_rate = score.get("average_heart_rate")
        row.max_heart_rate = score.get("max_heart_rate")
        row.raw_payload = payload

    def _upsert_recovery(self, account: SourceAccount, payload: dict) -> None:
        external_id = str(payload.get("cycle_id") or payload.get("id"))
        row = self.db.scalar(select(WhoopRecovery).where(WhoopRecovery.external_id == external_id))
        if row is None:
            row = WhoopRecovery(
                source_account_id=account.id,
                external_id=external_id,
                raw_payload=payload,
            )
            self.db.add(row)
        row.cycle_external_id = str(payload.get("cycle_id") or payload.get("id"))
        row.local_date = (
            WhoopClient.parse_datetime(payload.get("created_at")) or datetime.now(UTC)
        ).astimezone(self.local_tz).date()
        row.created_at_remote = WhoopClient.parse_datetime(payload.get("created_at"))
        row.updated_at_remote = WhoopClient.parse_datetime(payload.get("updated_at"))
        score = payload.get("score") or {}
        row.recovery_score = score.get("recovery_score")
        row.resting_heart_rate = score.get("resting_heart_rate")
        row.hrv_rmssd_ms = score.get("hrv_rmssd_milli")
        row.skin_temp_celsius = score.get("skin_temp_celsius")
        row.raw_payload = payload

    def _upsert_sleep(self, account: SourceAccount, payload: dict) -> None:
        row = self.db.scalar(select(WhoopSleep).where(WhoopSleep.external_id == str(payload["id"])))
        if row is None:
            row = WhoopSleep(
                source_account_id=account.id,
                external_id=str(payload["id"]),
                raw_payload=payload,
            )
            self.db.add(row)
        row.cycle_external_id = str(payload.get("cycle_id")) if payload.get("cycle_id") else None
        row.started_at = WhoopClient.parse_datetime(payload.get("start"))
        row.ended_at = WhoopClient.parse_datetime(payload.get("end"))
        base_dt = row.started_at or datetime.now(UTC)
        row.local_date = base_dt.astimezone(self.local_tz).date()
        score = payload.get("score") or {}
        row.total_sleep_minutes = self._milli_to_minutes(score.get("stage_summary", {}).get("total_in_bed_time_milli"))
        row.sleep_need_minutes = self._milli_to_minutes(payload.get("sleep_needed", {}).get("sleep_need_milli"))
        row.sleep_efficiency = score.get("sleep_efficiency_percentage")
        row.stage_summary_json = score.get("stage_summary")
        row.raw_payload = payload

    def _upsert_workout(self, account: SourceAccount, payload: dict) -> None:
        row = self.db.scalar(select(WhoopWorkout).where(WhoopWorkout.external_id == str(payload["id"])))
        if row is None:
            row = WhoopWorkout(
                source_account_id=account.id,
                external_id=str(payload["id"]),
                started_at=WhoopClient.parse_datetime(payload["start"]) or datetime.now(UTC),
                raw_payload=payload,
            )
            self.db.add(row)
        row.started_at = WhoopClient.parse_datetime(payload.get("start")) or row.started_at
        row.ended_at = WhoopClient.parse_datetime(payload.get("end"))
        row.local_date = row.started_at.astimezone(self.local_tz).date()
        row.sport_id = payload.get("sport_id")
        row.sport_name = payload.get("sport_name")
        row.score_state = payload.get("score_state")
        score = payload.get("score") or {}
        row.strain = score.get("strain")
        row.average_heart_rate = score.get("average_heart_rate")
        row.max_heart_rate = score.get("max_heart_rate")
        row.kilojoule = score.get("kilojoule")
        row.percent_recorded = score.get("percent_recorded")
        row.distance_meter = score.get("distance_meter")
        row.altitude_gain_meter = score.get("altitude_gain_meter")
        row.zone_durations_json = score.get("zone_durations")
        row.deleted_at = None
        row.raw_payload = payload

    def _upsert_body_measurement(self, account: SourceAccount, payload: dict) -> None:
        measured_on = datetime.now(self.local_tz).date()
        row = self.db.scalar(
            select(WhoopBodyMeasurement).where(
                WhoopBodyMeasurement.source_account_id == account.id,
                WhoopBodyMeasurement.measured_on == measured_on,
            )
        )
        if row is None:
            row = WhoopBodyMeasurement(
                source_account_id=account.id,
                measured_on=measured_on,
                raw_payload=payload,
            )
            self.db.add(row)
        row.height_meter = payload.get("height_meter")
        row.weight_kg = payload.get("weight_kilogram")
        row.max_heart_rate = payload.get("max_heart_rate")
        row.raw_payload = payload

    @staticmethod
    def _milli_to_minutes(value: int | float | None) -> int | None:
        if value is None:
            return None
        return int(round(float(value) / 60000))

    @staticmethod
    def _normalize_utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
