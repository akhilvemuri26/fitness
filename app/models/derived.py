from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.common import TimestampMixin, UUIDPrimaryKeyMixin


class LinkedWorkoutSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "linked_workout_sessions"
    __table_args__ = (
        UniqueConstraint("hevy_workout_id", name="uq_linked_workout_hevy"),
        UniqueConstraint("whoop_workout_id", name="uq_linked_workout_whoop"),
    )

    hevy_workout_id: Mapped[str] = mapped_column(
        ForeignKey("hevy_workouts.id", ondelete="CASCADE"), nullable=False
    )
    whoop_workout_id: Mapped[str] = mapped_column(
        ForeignKey("whoop_workouts.id", ondelete="CASCADE"), nullable=False
    )
    match_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    match_reason: Mapped[str] = mapped_column(String(255), nullable=False)
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

