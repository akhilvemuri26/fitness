from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import TimestampMixin, UUIDPrimaryKeyMixin


class MfpDaySummary(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "mfp_day_summaries"
    __table_args__ = (
        UniqueConstraint("source_account_id", "entry_date", name="uq_mfp_day_summary_source_date"),
    )

    source_account_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    calories: Mapped[float | None] = mapped_column(Float)
    protein_g: Mapped[float | None] = mapped_column(Float)
    carbs_g: Mapped[float | None] = mapped_column(Float)
    fat_g: Mapped[float | None] = mapped_column(Float)
    sugar_g: Mapped[float | None] = mapped_column(Float)
    fiber_g: Mapped[float | None] = mapped_column(Float)
    water_ml: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text)
    raw_payload: Mapped[dict] = mapped_column(JSON, nullable=False)

    meals: Mapped[list[MfpMealEntry]] = relationship(
        back_populates="day_summary", cascade="all, delete-orphan"
    )
    water_entries: Mapped[list[MfpWaterEntry]] = relationship(
        back_populates="day_summary", cascade="all, delete-orphan"
    )
    weight_entries: Mapped[list[MfpWeightEntry]] = relationship(
        back_populates="day_summary", cascade="all, delete-orphan"
    )


class MfpMealEntry(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "mfp_meal_entries"

    day_summary_id: Mapped[str] = mapped_column(
        ForeignKey("mfp_day_summaries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    meal_name: Mapped[str] = mapped_column(String(120), nullable=False)
    food_name: Mapped[str] = mapped_column(String(255), nullable=False)
    serving_size: Mapped[str | None] = mapped_column(String(120))
    calories: Mapped[float | None] = mapped_column(Float)
    protein_g: Mapped[float | None] = mapped_column(Float)
    carbs_g: Mapped[float | None] = mapped_column(Float)
    fat_g: Mapped[float | None] = mapped_column(Float)
    nutrition_json: Mapped[dict | None] = mapped_column(JSON)

    day_summary: Mapped[MfpDaySummary] = relationship(back_populates="meals")


class MfpWaterEntry(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "mfp_water_entries"

    day_summary_id: Mapped[str] = mapped_column(
        ForeignKey("mfp_day_summaries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entry_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    milliliters: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    cups: Mapped[float | None] = mapped_column(Float)

    day_summary: Mapped[MfpDaySummary] = relationship(back_populates="water_entries")


class MfpWeightEntry(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "mfp_weight_entries"

    day_summary_id: Mapped[str] = mapped_column(
        ForeignKey("mfp_day_summaries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entry_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False, default="pounds")
    measured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    day_summary: Mapped[MfpDaySummary] = relationship(back_populates="weight_entries")

