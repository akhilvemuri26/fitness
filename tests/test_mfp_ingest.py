from app.models.mfp import MfpDaySummary, MfpMealEntry
from app.models.source import SourceAccount, SyncCursor
from app.schemas.mfp import MfpMealPayload, MfpSyncBatchRequest, MfpDayPayload
from app.services.mfp_ingest import MfpIngestService


def test_mfp_ingest_is_idempotent(db_session) -> None:
    service = MfpIngestService(db_session)
    payload = MfpSyncBatchRequest(
        days=[
            MfpDayPayload(
                entry_date="2026-04-06",
                calories=2200,
                protein_g=180,
                carbs_g=210,
                fat_g=70,
                water_ml=3000,
                raw_payload={"source": "test"},
                meals=[
                    MfpMealPayload(
                        meal_name="Breakfast",
                        food_name="Eggs",
                        calories=300,
                        protein_g=25,
                    )
                ],
            )
        ]
    )

    service.ingest_batch(payload)
    service.ingest_batch(payload)

    assert db_session.query(SourceAccount).count() == 1
    assert db_session.query(MfpDaySummary).count() == 1
    assert db_session.query(MfpMealEntry).count() == 1
    assert db_session.query(SyncCursor).count() == 1

