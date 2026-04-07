from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.derived import LinkedWorkoutSession
from app.models.hevy import HevyWorkout, HevyWorkoutExercise, HevyWorkoutSet
from app.models.mfp import MfpDaySummary, MfpWeightEntry
from app.models.source import SourceAccount, SourceType
from app.models.whoop import (
    WhoopBodyMeasurement,
    WhoopCycle,
    WhoopRecovery,
    WhoopSleep,
    WhoopWorkout,
)


@dataclass(slots=True)
class DashboardWorkout:
    title: str
    started_at: str
    ended_at: str
    exercise_count: int
    set_count: int
    whoop_strain: float | None


class DashboardService:
    healthy_sync_window = timedelta(hours=2)
    attention_sync_window = timedelta(hours=24)

    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.local_tz = ZoneInfo(self.settings.canonical_timezone)

    def build_dashboard_context(self, selected_date: date | None) -> dict:
        target_date = selected_date or datetime.now(self.local_tz).date()
        nutrition = self._nutrition_summary(target_date)
        recovery = self._recovery_summary(target_date)
        sleep = self._sleep_summary(target_date)
        cycle = self._cycle_summary(target_date)
        body = self._body_summary(target_date)
        workouts = self._workout_cards(target_date)
        return {
            "title": f"Fitness Hub · {target_date.isoformat()}",
            "request": None,
            "dashboard": {
                "selected_date": target_date.isoformat(),
                "nutrition": nutrition,
                "recovery": recovery,
                "sleep": sleep,
                "cycle": cycle,
                "body": body,
                "workouts": workouts,
            },
            "sync_status": self._sync_status(),
        }

    def build_connections_context(self) -> dict:
        rows = self.db.scalars(select(SourceAccount).order_by(SourceAccount.source_type)).all()
        known = {row.source_type: row for row in rows}
        sources = []
        for source_type, label, description in [
            (SourceType.WHOOP.value, "WHOOP", "OAuth integration for recovery, sleep, strain, and biometrics."),
            (SourceType.HEVY.value, "Hevy", "API key integration for workouts, templates, and workout events."),
            (SourceType.MYFITNESSPAL.value, "MyFitnessPal", "Local bridge worker for nutrition, hydration, and weight."),
        ]:
            row = known.get(source_type)
            status = row.status if row else "disconnected"
            last_synced_at = self._normalize_dt(row.last_synced_at) if row else None
            sync_health = self._sync_health(source_type, status, last_synced_at)
            sources.append(
                {
                    "label": label,
                    "description": description,
                    "status": status,
                    "status_label": self._status_label(status),
                    "last_synced_at": self._format_dt(last_synced_at),
                    "cursor": self._cursor_summary(row) if row else None,
                    "sync_model": self._sync_model(source_type),
                    "sync_source": self._sync_source(source_type),
                    "freshness_label": sync_health["label"],
                    "freshness_tone": sync_health["tone"],
                    "freshness_hint": sync_health["hint"],
                    "error_message": row.last_error if row and row.last_error else None,
                    "action_href": self._action_href(source_type, status),
                    "action_label": self._action_label(source_type, status),
                }
            )
        return {"title": "Fitness Hub · Connections", "request": None, "sources": sources}

    def _nutrition_summary(self, target_date: date) -> dict:
        day = self.db.scalar(select(MfpDaySummary).where(MfpDaySummary.entry_date == target_date))
        latest_weight = self.db.scalar(
            select(MfpWeightEntry)
            .where(MfpWeightEntry.entry_date == target_date)
            .order_by(MfpWeightEntry.measured_at.desc().nullslast())
        )
        return {
            "calories": round(day.calories or 0, 1) if day else 0,
            "protein": round(day.protein_g or 0, 1) if day else 0,
            "carbs": round(day.carbs_g or 0, 1) if day else 0,
            "fat": round(day.fat_g or 0, 1) if day else 0,
            "water_ml": round(day.water_ml or 0, 1) if day else 0,
            "weight": f"{latest_weight.value:.1f} {latest_weight.unit}" if latest_weight else "N/A",
        }

    def _recovery_summary(self, target_date: date) -> dict:
        row = self.db.scalar(
            select(WhoopRecovery)
            .where(WhoopRecovery.local_date == target_date)
            .order_by(WhoopRecovery.created_at_remote.desc().nullslast())
        )
        return {
            "recovery_score": round(row.recovery_score, 1) if row and row.recovery_score is not None else "N/A",
            "hrv_ms": round(row.hrv_rmssd_ms, 1) if row and row.hrv_rmssd_ms is not None else "N/A",
            "resting_hr": row.resting_heart_rate if row and row.resting_heart_rate is not None else "N/A",
        }

    def _sleep_summary(self, target_date: date) -> dict:
        row = self.db.scalar(select(WhoopSleep).where(WhoopSleep.local_date == target_date))
        return {
            "sleep_need_minutes": row.sleep_need_minutes if row and row.sleep_need_minutes is not None else "N/A",
            "total_sleep_minutes": row.total_sleep_minutes if row and row.total_sleep_minutes is not None else "N/A",
            "sleep_efficiency": round(row.sleep_efficiency, 2) if row and row.sleep_efficiency is not None else "N/A",
        }

    def _cycle_summary(self, target_date: date) -> dict:
        row = self.db.scalar(select(WhoopCycle).where(WhoopCycle.local_date == target_date))
        return {
            "strain": round(row.strain, 2) if row and row.strain is not None else "N/A",
            "avg_hr": row.average_heart_rate if row and row.average_heart_rate is not None else "N/A",
        }

    def _body_summary(self, target_date: date) -> dict:
        row = self.db.scalar(
            select(WhoopBodyMeasurement)
            .where(WhoopBodyMeasurement.measured_on <= target_date)
            .order_by(WhoopBodyMeasurement.measured_on.desc())
        )
        return {
            "max_heart_rate": row.max_heart_rate if row and row.max_heart_rate is not None else "N/A",
            "weight": f"{row.weight_kg:.1f} kg" if row and row.weight_kg is not None else "N/A",
            "height": f"{row.height_meter:.2f} m" if row and row.height_meter is not None else "N/A",
        }

    def _workout_cards(self, target_date: date) -> list[dict]:
        stmt = (
            select(
                HevyWorkout.title,
                HevyWorkout.started_at,
                HevyWorkout.ended_at,
                func.count(func.distinct(HevyWorkoutExercise.id)).label("exercise_count"),
                func.count(func.distinct(HevyWorkoutSet.id)).label("set_count"),
                WhoopWorkout.strain,
            )
            .select_from(HevyWorkout)
            .outerjoin(HevyWorkoutExercise, HevyWorkoutExercise.workout_id == HevyWorkout.id)
            .outerjoin(HevyWorkoutSet, HevyWorkoutSet.exercise_id == HevyWorkoutExercise.id)
            .outerjoin(LinkedWorkoutSession, LinkedWorkoutSession.hevy_workout_id == HevyWorkout.id)
            .outerjoin(WhoopWorkout, WhoopWorkout.id == LinkedWorkoutSession.whoop_workout_id)
            .where(HevyWorkout.local_date == target_date, HevyWorkout.is_deleted.is_(False))
            .group_by(HevyWorkout.id, WhoopWorkout.strain)
            .order_by(HevyWorkout.started_at.asc())
        )
        rows = self.db.execute(stmt).all()
        cards = []
        for row in rows:
            cards.append(
                asdict(
                    DashboardWorkout(
                        title=row.title,
                        started_at=row.started_at.astimezone(self.local_tz).strftime("%I:%M %p"),
                        ended_at=(
                            row.ended_at.astimezone(self.local_tz).strftime("%I:%M %p")
                            if row.ended_at
                            else "In progress"
                        ),
                        exercise_count=row.exercise_count,
                        set_count=row.set_count,
                        whoop_strain=row.strain,
                    )
                )
            )
        return cards

    def _sync_status(self) -> list[dict]:
        rows = self.db.scalars(select(SourceAccount).order_by(SourceAccount.source_type)).all()
        labels = {
            SourceType.WHOOP.value: "WHOOP",
            SourceType.HEVY.value: "Hevy",
            SourceType.MYFITNESSPAL.value: "MyFitnessPal",
        }
        items = []
        for row in rows:
            last_synced_at = self._normalize_dt(row.last_synced_at)
            sync_health = self._sync_health(row.source_type, row.status, last_synced_at)
            items.append(
                {
                    "label": labels.get(row.source_type, row.source_type.title()),
                    "state": sync_health["label"],
                    "state_detail": self._status_label(row.status),
                    "last_synced_at": self._format_dt(last_synced_at),
                    "sync_model": self._sync_model(row.source_type),
                    "freshness_tone": sync_health["tone"],
                }
            )
        return items

    @staticmethod
    def _status_label(status: str) -> str:
        return {
            "connected": "Connected",
            "disconnected": "Disconnected",
            "error": "Error",
            "needs_attention": "Needs attention",
            "oauth_ready": "Ready to connect",
            "ready_to_sync": "Ready to sync",
            "waiting_for_bridge": "Waiting for bridge sync",
        }.get(status, status.replace("_", " ").title())

    @staticmethod
    def _action_href(source_type: str, status: str) -> str | None:
        if source_type == SourceType.WHOOP.value and status != "connected":
            return "/connect/whoop/start"
        if source_type == SourceType.WHOOP.value:
            return "/actions/sync/whoop"
        if source_type == SourceType.HEVY.value:
            return "/actions/sync/hevy"
        return None

    @staticmethod
    def _action_label(source_type: str, status: str) -> str | None:
        if source_type == SourceType.WHOOP.value and status != "connected":
            return "Connect WHOOP"
        if source_type == SourceType.WHOOP.value:
            return "Sync WHOOP now"
        if source_type == SourceType.HEVY.value:
            return "Sync Hevy now"
        return None

    def _sync_health(self, source_type: str, status: str, last_synced_at: datetime | None) -> dict[str, str]:
        if status == "error":
            return {
                "label": "Attention needed",
                "tone": "attention",
                "hint": "The most recent sync failed and needs a retry.",
            }
        if status in {"disconnected", "oauth_ready", "ready_to_sync", "waiting_for_bridge"}:
            return {
                "label": self._status_label(status),
                "tone": "neutral",
                "hint": self._connectivity_hint(source_type, status),
            }
        if last_synced_at is None:
            return {
                "label": "Awaiting first sync",
                "tone": "neutral",
                "hint": self._connectivity_hint(source_type, status),
            }

        age = datetime.now(UTC) - last_synced_at
        if age <= self.healthy_sync_window:
            return {
                "label": "Healthy",
                "tone": "healthy",
                "hint": self._healthy_hint(source_type),
            }
        if age <= self.attention_sync_window:
            return {
                "label": "Stale",
                "tone": "stale",
                "hint": "No fresh sync has landed recently. A manual sync is safe to run.",
            }
        return {
            "label": "Attention needed",
            "tone": "attention",
            "hint": "This source has not synced in over 24 hours.",
        }

    @staticmethod
    def _sync_model(source_type: str) -> str:
        if source_type == SourceType.MYFITNESSPAL.value:
            return "Mac-dependent bridge"
        return "Hosted auto-sync"

    @staticmethod
    def _sync_source(source_type: str) -> str:
        if source_type == SourceType.WHOOP.value:
            return "GitHub Actions -> internal WHOOP reconcile endpoint"
        if source_type == SourceType.HEVY.value:
            return "GitHub Actions -> internal Hevy sync endpoint"
        if source_type == SourceType.MYFITNESSPAL.value:
            return "launchd on your Mac -> local MFP bridge"
        return "Manual"

    @staticmethod
    def _healthy_hint(source_type: str) -> str:
        if source_type == SourceType.MYFITNESSPAL.value:
            return "Recent bridge sync received. This source still depends on your Mac being awake."
        return "Recent hosted sync received."

    @staticmethod
    def _connectivity_hint(source_type: str, status: str) -> str:
        if source_type == SourceType.MYFITNESSPAL.value:
            if status == "waiting_for_bridge":
                return "The hosted app is ready. Install the local launch agent or run the bridge manually."
            return "MyFitnessPal still needs a local bridge run before data will appear."
        if source_type == SourceType.WHOOP.value:
            return "WHOOP is ready once you complete OAuth."
        if source_type == SourceType.HEVY.value:
            return "Hevy is ready once the first sync completes."
        return "This source needs attention."

    def _format_dt(self, value: datetime | None) -> str | None:
        normalized = self._normalize_dt(value)
        if normalized is None:
            return None
        return normalized.astimezone(self.local_tz).strftime("%Y-%m-%d %I:%M %p")

    @staticmethod
    def _normalize_dt(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @staticmethod
    def _cursor_summary(row: SourceAccount | None) -> str | None:
        if row is None or not row.sync_cursors:
            return None
        latest = max(
            row.sync_cursors,
            key=lambda cursor: cursor.synced_at or cursor.created_at,
        )
        return f"{latest.cursor_key}: {latest.cursor_value or 'set'}"
