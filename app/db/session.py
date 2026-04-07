from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


settings = get_settings()
connect_args: dict[str, object] = {}
if settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(settings.database_url, future=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

DAILY_HEALTH_SUMMARY_VIEW_SQL = """
CREATE VIEW IF NOT EXISTS daily_health_summary AS
WITH summary_dates AS (
    SELECT entry_date AS summary_date FROM mfp_day_summaries
    UNION
    SELECT local_date AS summary_date FROM whoop_cycles
    UNION
    SELECT local_date AS summary_date FROM whoop_recoveries
    UNION
    SELECT local_date AS summary_date FROM whoop_sleeps
    UNION
    SELECT local_date AS summary_date FROM hevy_workouts WHERE is_deleted = false
)
SELECT
    summary_dates.summary_date,
    nutrition.calories,
    nutrition.protein_g,
    nutrition.carbs_g,
    nutrition.fat_g,
    nutrition.water_ml,
    cycle.strain AS cycle_strain,
    cycle.average_heart_rate AS cycle_average_heart_rate,
    recovery.recovery_score,
    recovery.hrv_rmssd_ms,
    recovery.resting_heart_rate,
    sleep.total_sleep_minutes,
    sleep.sleep_need_minutes,
    sleep.sleep_efficiency,
    body.weight_kg AS whoop_weight_kg,
    body.height_meter,
    body.max_heart_rate,
    workout_counts.workout_count
FROM summary_dates
LEFT JOIN mfp_day_summaries AS nutrition
    ON nutrition.entry_date = summary_dates.summary_date
LEFT JOIN whoop_cycles AS cycle
    ON cycle.local_date = summary_dates.summary_date
LEFT JOIN whoop_recoveries AS recovery
    ON recovery.local_date = summary_dates.summary_date
LEFT JOIN whoop_sleeps AS sleep
    ON sleep.local_date = summary_dates.summary_date
LEFT JOIN whoop_body_measurements AS body
    ON body.measured_on = summary_dates.summary_date
LEFT JOIN (
    SELECT local_date, COUNT(*) AS workout_count
    FROM hevy_workouts
    WHERE is_deleted = false
    GROUP BY local_date
) AS workout_counts
    ON workout_counts.local_date = summary_dates.summary_date
"""


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_schema_if_needed() -> None:
    from app.models import all_models  # noqa: F401

    from app.db.base import Base

    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        connection.execute(text(DAILY_HEALTH_SUMMARY_VIEW_SQL))
