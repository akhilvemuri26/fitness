from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.mfp import MfpDaySummary, MfpMealEntry, MfpWaterEntry, MfpWeightEntry
from app.models.source import SourceStatus, SourceType
from app.schemas.mfp import MfpSyncBatchRequest
from app.services.source_accounts import SourceAccountService


class MfpIngestService:
    def __init__(self, db: Session):
        self.db = db
        self.source_service = SourceAccountService(db)

    def ingest_batch(self, payload: MfpSyncBatchRequest) -> dict:
        account = self.source_service.get_or_create(SourceType.MYFITNESSPAL, "MyFitnessPal")
        for day_payload in payload.days:
            existing = self.db.scalar(
                select(MfpDaySummary).where(
                    MfpDaySummary.source_account_id == account.id,
                    MfpDaySummary.entry_date == day_payload.entry_date,
                )
            )
            if existing is None:
                existing = MfpDaySummary(
                    source_account_id=account.id,
                    entry_date=day_payload.entry_date,
                    raw_payload={},
                )
                self.db.add(existing)
                self.db.flush()

            existing.calories = day_payload.calories
            existing.protein_g = day_payload.protein_g
            existing.carbs_g = day_payload.carbs_g
            existing.fat_g = day_payload.fat_g
            existing.sugar_g = day_payload.sugar_g
            existing.fiber_g = day_payload.fiber_g
            existing.water_ml = day_payload.water_ml
            existing.notes = day_payload.notes
            existing.raw_payload = day_payload.raw_payload

            self.db.execute(delete(MfpMealEntry).where(MfpMealEntry.day_summary_id == existing.id))
            self.db.execute(delete(MfpWaterEntry).where(MfpWaterEntry.day_summary_id == existing.id))
            self.db.execute(delete(MfpWeightEntry).where(MfpWeightEntry.day_summary_id == existing.id))

            for meal in day_payload.meals:
                self.db.add(
                    MfpMealEntry(
                        day_summary_id=existing.id,
                        meal_name=meal.meal_name,
                        food_name=meal.food_name,
                        serving_size=meal.serving_size,
                        calories=meal.calories,
                        protein_g=meal.protein_g,
                        carbs_g=meal.carbs_g,
                        fat_g=meal.fat_g,
                        nutrition_json=meal.nutrition_json,
                    )
                )

            if day_payload.water_ml is not None:
                self.db.add(
                    MfpWaterEntry(
                        day_summary_id=existing.id,
                        entry_date=day_payload.entry_date,
                        milliliters=day_payload.water_ml,
                        cups=(day_payload.water_ml / 236.588) if day_payload.water_ml else 0,
                    )
                )

            for weight in day_payload.weight_entries:
                self.db.add(
                    MfpWeightEntry(
                        day_summary_id=existing.id,
                        entry_date=day_payload.entry_date,
                        value=weight.value,
                        unit=weight.unit,
                        measured_at=weight.measured_at,
                    )
                )

        account.status = SourceStatus.CONNECTED.value
        account.last_synced_at = datetime.now(timezone.utc)
        account.credentials_json = {
            **(account.credentials_json or {}),
            "last_batch_size": len(payload.days),
        }
        if payload.days:
            last_date = max(day.entry_date for day in payload.days).isoformat()
            self.source_service.set_cursor(account, "last_batch_date", last_date)
        self.db.commit()
        return {"ingested_days": len(payload.days)}

