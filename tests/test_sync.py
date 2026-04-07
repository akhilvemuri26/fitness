from datetime import UTC, datetime, timedelta

from app.models.source import SourceAccount, SourceType
from app.services.sync import WhoopSyncService


def test_whoop_refresh_handles_naive_sqlite_expiry(db_session) -> None:
    service = WhoopSyncService(db_session)
    account = SourceAccount(
        source_type=SourceType.WHOOP.value,
        label="WHOOP",
        status="connected",
        access_token="token",
        refresh_token="refresh",
        token_expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=1),
        credentials_json={},
        profile_json={},
    )

    normalized = service._normalize_utc(account.token_expires_at)

    assert normalized is not None
    assert normalized.tzinfo == UTC
