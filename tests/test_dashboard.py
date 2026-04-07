from datetime import UTC, datetime, timedelta

from app.models.source import SourceAccount, SyncCursor
from app.services.dashboard import DashboardService


def test_connections_context_marks_recent_hosted_sync_as_healthy(db_session) -> None:
    account = SourceAccount(
        source_type="whoop",
        label="WHOOP",
        status="connected",
        credentials_json={},
        profile_json={},
        last_synced_at=datetime.now(UTC) - timedelta(minutes=45),
    )
    db_session.add(account)
    db_session.flush()
    db_session.add(
        SyncCursor(
            source_account_id=account.id,
            cursor_key="collections_since",
            cursor_value="2026-04-06T12:00:00+00:00",
            synced_at=datetime.now(UTC),
        )
    )
    db_session.commit()

    context = DashboardService(db_session).build_connections_context()
    whoop = next(item for item in context["sources"] if item["label"] == "WHOOP")

    assert whoop["freshness_label"] == "Healthy"
    assert whoop["sync_model"] == "Hosted auto-sync"
    assert whoop["cursor"] == "collections_since: 2026-04-06T12:00:00+00:00"


def test_connections_context_marks_old_mfp_sync_as_stale(db_session) -> None:
    account = SourceAccount(
        source_type="myfitnesspal",
        label="MyFitnessPal",
        status="connected",
        credentials_json={},
        profile_json={},
        last_synced_at=(datetime.now(UTC) - timedelta(hours=4)).replace(tzinfo=None),
    )
    db_session.add(account)
    db_session.commit()

    context = DashboardService(db_session).build_connections_context()
    mfp = next(item for item in context["sources"] if item["label"] == "MyFitnessPal")

    assert mfp["freshness_label"] == "Stale"
    assert mfp["freshness_tone"] == "stale"
    assert mfp["sync_model"] == "Mac-dependent bridge"
