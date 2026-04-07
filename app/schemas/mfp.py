from datetime import date, datetime

from pydantic import BaseModel, Field


class MfpMealPayload(BaseModel):
    meal_name: str
    food_name: str
    serving_size: str | None = None
    calories: float | None = None
    protein_g: float | None = None
    carbs_g: float | None = None
    fat_g: float | None = None
    nutrition_json: dict | None = None


class MfpWeightPayload(BaseModel):
    value: float
    unit: str = "pounds"
    measured_at: datetime | None = None


class MfpDayPayload(BaseModel):
    entry_date: date
    calories: float | None = None
    protein_g: float | None = None
    carbs_g: float | None = None
    fat_g: float | None = None
    sugar_g: float | None = None
    fiber_g: float | None = None
    water_ml: float | None = None
    notes: str | None = None
    raw_payload: dict = Field(default_factory=dict)
    meals: list[MfpMealPayload] = Field(default_factory=list)
    weight_entries: list[MfpWeightPayload] = Field(default_factory=list)


class MfpSyncBatchRequest(BaseModel):
    days: list[MfpDayPayload]

