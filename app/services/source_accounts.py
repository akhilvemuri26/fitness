from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.source import RawIngestEvent, SourceAccount, SourceStatus, SourceType, SyncCursor


class SourceAccountService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def get_or_create(self, source_type: SourceType, label: str) -> SourceAccount:
        account = self.db.scalar(
            select(SourceAccount).where(SourceAccount.source_type == source_type.value)
        )
        if account:
            return account

        account = SourceAccount(
            source_type=source_type.value,
            label=label,
            status=SourceStatus.DISCONNECTED.value,
            credentials_json={},
            profile_json={},
        )
        self.db.add(account)
        self.db.flush()
        return account

    def bootstrap_defaults(self) -> None:
        defaults = [
            (SourceType.WHOOP, "WHOOP"),
            (SourceType.HEVY, "Hevy"),
            (SourceType.MYFITNESSPAL, "MyFitnessPal"),
        ]
        for source_type, label in defaults:
            account = self.get_or_create(source_type, label)
            inferred = self._infer_status(source_type, account)
            if account.status in {
                SourceStatus.DISCONNECTED.value,
                "oauth_ready",
                "ready_to_sync",
                "waiting_for_bridge",
            }:
                account.status = inferred
        self.db.commit()

    def get(self, source_type: SourceType) -> SourceAccount | None:
        return self.db.scalar(
            select(SourceAccount).where(SourceAccount.source_type == source_type.value)
        )

    def set_status(
        self,
        account: SourceAccount,
        *,
        status: SourceStatus,
        last_error: str | None = None,
        last_synced_at: datetime | None = None,
    ) -> None:
        account.status = status.value
        account.last_error = last_error
        if last_synced_at:
            account.last_synced_at = last_synced_at

    def get_cursor(self, account: SourceAccount, cursor_key: str) -> SyncCursor | None:
        return self.db.scalar(
            select(SyncCursor).where(
                SyncCursor.source_account_id == account.id,
                SyncCursor.cursor_key == cursor_key,
            )
        )

    def set_cursor(self, account: SourceAccount, cursor_key: str, cursor_value: str | None) -> SyncCursor:
        cursor = self.get_cursor(account, cursor_key)
        if cursor is None:
            cursor = SyncCursor(
                source_account_id=account.id,
                cursor_key=cursor_key,
            )
            self.db.add(cursor)
        cursor.cursor_value = cursor_value
        cursor.synced_at = datetime.now(timezone.utc)
        self.db.flush()
        return cursor

    def record_raw_event(
        self,
        *,
        source_type: SourceType,
        event_type: str,
        payload: dict,
        external_id: str | None = None,
        occurred_at: datetime | None = None,
    ) -> RawIngestEvent:
        event = RawIngestEvent(
            source_type=source_type.value,
            event_type=event_type,
            external_id=external_id,
            occurred_at=occurred_at,
            received_at=datetime.now(timezone.utc),
            payload=payload,
        )
        self.db.add(event)
        self.db.flush()
        return event

    def _infer_status(self, source_type: SourceType, account: SourceAccount) -> str:
        if source_type is SourceType.WHOOP:
            if account.access_token:
                return SourceStatus.CONNECTED.value
            if self.settings.whoop_client_id and self.settings.whoop_client_secret:
                return "oauth_ready"
            return SourceStatus.DISCONNECTED.value

        if source_type is SourceType.HEVY:
            if account.last_synced_at:
                return SourceStatus.CONNECTED.value
            if self.settings.hevy_api_key:
                return "ready_to_sync"
            return SourceStatus.DISCONNECTED.value

        if source_type is SourceType.MYFITNESSPAL:
            if account.last_synced_at:
                return SourceStatus.CONNECTED.value
            if self.settings.mfp_bridge_shared_token:
                return "waiting_for_bridge"
            return SourceStatus.DISCONNECTED.value

        return SourceStatus.DISCONNECTED.value
