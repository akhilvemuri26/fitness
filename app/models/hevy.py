from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import TimestampMixin, UUIDPrimaryKeyMixin


class HevyWorkout(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "hevy_workouts"
    __table_args__ = (UniqueConstraint("external_id", name="uq_hevy_workout_external"),)

    source_account_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(120), nullable=False)
    local_date: Mapped[date | None] = mapped_column(Date, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    routine_id: Mapped[str | None] = mapped_column(String(120))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at_remote: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at_remote: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSON, nullable=False)

    exercises: Mapped[list[HevyWorkoutExercise]] = relationship(
        back_populates="workout",
        cascade="all, delete-orphan",
        order_by="HevyWorkoutExercise.exercise_index",
    )


class HevyWorkoutExercise(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "hevy_workout_exercises"

    workout_id: Mapped[str] = mapped_column(
        ForeignKey("hevy_workouts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    exercise_index: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    exercise_template_id: Mapped[str | None] = mapped_column(String(120), index=True)
    superset_id: Mapped[int | None] = mapped_column(Integer)

    workout: Mapped[HevyWorkout] = relationship(back_populates="exercises")
    sets: Mapped[list[HevyWorkoutSet]] = relationship(
        back_populates="exercise",
        cascade="all, delete-orphan",
        order_by="HevyWorkoutSet.set_index",
    )


class HevyWorkoutSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "hevy_workout_sets"

    exercise_id: Mapped[str] = mapped_column(
        ForeignKey("hevy_workout_exercises.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    set_index: Mapped[int] = mapped_column(Integer, nullable=False)
    set_type: Mapped[str | None] = mapped_column(String(32))
    weight_kg: Mapped[float | None] = mapped_column(Float)
    reps: Mapped[int | None] = mapped_column(Integer)
    distance_meters: Mapped[float | None] = mapped_column(Float)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    rpe: Mapped[float | None] = mapped_column(Float)
    custom_metric: Mapped[float | None] = mapped_column(Float)

    exercise: Mapped[HevyWorkoutExercise] = relationship(back_populates="sets")


class HevyExerciseTemplate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "hevy_exercise_templates"
    __table_args__ = (
        UniqueConstraint("external_id", name="uq_hevy_exercise_template_external"),
    )

    source_account_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    exercise_type: Mapped[str | None] = mapped_column(String(64))
    primary_muscle_group: Mapped[str | None] = mapped_column(String(120))
    secondary_muscle_groups_json: Mapped[list | None] = mapped_column(JSON)
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSON, nullable=False)

