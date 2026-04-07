from app.models.derived import LinkedWorkoutSession
from app.models.hevy import HevyExerciseTemplate, HevyWorkout, HevyWorkoutExercise, HevyWorkoutSet
from app.models.mfp import MfpDaySummary, MfpMealEntry, MfpWaterEntry, MfpWeightEntry
from app.models.source import RawIngestEvent, SourceAccount, SyncCursor
from app.models.whoop import (
    WhoopBodyMeasurement,
    WhoopCycle,
    WhoopRecovery,
    WhoopSleep,
    WhoopWorkout,
)

all_models = [
    SourceAccount,
    SyncCursor,
    RawIngestEvent,
    HevyWorkout,
    HevyWorkoutExercise,
    HevyWorkoutSet,
    HevyExerciseTemplate,
    WhoopCycle,
    WhoopRecovery,
    WhoopSleep,
    WhoopWorkout,
    WhoopBodyMeasurement,
    MfpDaySummary,
    MfpMealEntry,
    MfpWaterEntry,
    MfpWeightEntry,
    LinkedWorkoutSession,
]

