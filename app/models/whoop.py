from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.common import TimestampMixin, UUIDPrimaryKeyMixin


class WhoopCycle(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "whoop_cycles"
    __table_args__ = (UniqueConstraint("external_id", name="uq_whoop_cycle_external"),)

    source_account_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(120), nullable=False)
    local_date: Mapped[date | None] = mapped_column(Date, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    timezone_offset: Mapped[str | None] = mapped_column(String(16))
    score_state: Mapped[str | None] = mapped_column(String(32))
    strain: Mapped[float | None] = mapped_column(Float)
    kilojoule: Mapped[float | None] = mapped_column(Float)
    average_heart_rate: Mapped[int | None] = mapped_column(Integer)
    max_heart_rate: Mapped[int | None] = mapped_column(Integer)
    raw_payload: Mapped[dict] = mapped_column(JSON, nullable=False)


class WhoopRecovery(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "whoop_recoveries"
    __table_args__ = (
        UniqueConstraint("external_id", name="uq_whoop_recovery_external"),
    )

    source_account_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(120), nullable=False)
    cycle_external_id: Mapped[str | None] = mapped_column(String(120), index=True)
    local_date: Mapped[date | None] = mapped_column(Date, index=True)
    created_at_remote: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at_remote: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recovery_score: Mapped[float | None] = mapped_column(Float)
    resting_heart_rate: Mapped[int | None] = mapped_column(Integer)
    hrv_rmssd_ms: Mapped[float | None] = mapped_column(Float)
    skin_temp_celsius: Mapped[float | None] = mapped_column(Float)
    raw_payload: Mapped[dict] = mapped_column(JSON, nullable=False)


class WhoopSleep(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "whoop_sleeps"
    __table_args__ = (UniqueConstraint("external_id", name="uq_whoop_sleep_external"),)

    source_account_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(120), nullable=False)
    cycle_external_id: Mapped[str | None] = mapped_column(String(120), index=True)
    local_date: Mapped[date | None] = mapped_column(Date, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_sleep_minutes: Mapped[int | None] = mapped_column(Integer)
    sleep_need_minutes: Mapped[int | None] = mapped_column(Integer)
    sleep_efficiency: Mapped[float | None] = mapped_column(Float)
    stage_summary_json: Mapped[dict | None] = mapped_column(JSON)
    raw_payload: Mapped[dict] = mapped_column(JSON, nullable=False)


class WhoopWorkout(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "whoop_workouts"
    __table_args__ = (UniqueConstraint("external_id", name="uq_whoop_workout_external"),)

    source_account_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(120), nullable=False)
    local_date: Mapped[date | None] = mapped_column(Date, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sport_id: Mapped[int | None] = mapped_column(Integer)
    sport_name: Mapped[str | None] = mapped_column(String(120))
    score_state: Mapped[str | None] = mapped_column(String(32))
    strain: Mapped[float | None] = mapped_column(Float)
    average_heart_rate: Mapped[int | None] = mapped_column(Integer)
    max_heart_rate: Mapped[int | None] = mapped_column(Integer)
    kilojoule: Mapped[float | None] = mapped_column(Float)
    percent_recorded: Mapped[float | None] = mapped_column(Float)
    distance_meter: Mapped[float | None] = mapped_column(Float)
    altitude_gain_meter: Mapped[float | None] = mapped_column(Float)
    zone_durations_json: Mapped[dict | None] = mapped_column(JSON)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    raw_payload: Mapped[dict] = mapped_column(JSON, nullable=False)


class WhoopBodyMeasurement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "whoop_body_measurements"
    __table_args__ = (
        UniqueConstraint("source_account_id", "measured_on", name="uq_whoop_body_measurement_day"),
    )

    source_account_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    measured_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    height_meter: Mapped[float | None] = mapped_column(Float)
    weight_kg: Mapped[float | None] = mapped_column(Float)
    max_heart_rate: Mapped[int | None] = mapped_column(Integer)
    raw_payload: Mapped[dict] = mapped_column(JSON, nullable=False)

