from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import TimestampMixin, UUIDPrimaryKeyMixin


class SourceType(StrEnum):
    WHOOP = "whoop"
    HEVY = "hevy"
    MYFITNESSPAL = "myfitnesspal"


class SourceStatus(StrEnum):
    DISCONNECTED = "disconnected"
    CONNECTED = "connected"
    ERROR = "error"
    NEEDS_ATTENTION = "needs_attention"


class SourceAccount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "source_accounts"

    source_type: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="disconnected")
    external_user_id: Mapped[str | None] = mapped_column(String(255))
    profile_json: Mapped[dict | None] = mapped_column(JSON)
    credentials_json: Mapped[dict | None] = mapped_column(JSON)
    access_token: Mapped[str | None] = mapped_column(Text)
    refresh_token: Mapped[str | None] = mapped_column(Text)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)

    sync_cursors: Mapped[list[SyncCursor]] = relationship(
        back_populates="source_account", cascade="all, delete-orphan"
    )


class SyncCursor(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sync_cursors"
    __table_args__ = (
        UniqueConstraint("source_account_id", "cursor_key", name="uq_sync_cursor_source_key"),
    )

    source_account_id: Mapped[str] = mapped_column(
        ForeignKey("source_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cursor_key: Mapped[str] = mapped_column(String(120), nullable=False)
    cursor_value: Mapped[str | None] = mapped_column(Text)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    source_account: Mapped[SourceAccount] = relationship("SourceAccount", back_populates="sync_cursors")


class RawIngestEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "raw_ingest_events"

    source_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(255), index=True)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
