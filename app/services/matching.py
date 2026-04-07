from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(slots=True)
class MatchCandidate:
    id: str
    started_at: datetime
    ended_at: datetime | None


@dataclass(slots=True)
class MatchResult:
    target_id: str | None
    confidence: float
    reason: str


class WorkoutMatcher:
    def __init__(self, proximity_minutes: int = 45):
        self.proximity_minutes = proximity_minutes

    def match(
        self,
        hevy_workout: MatchCandidate,
        whoop_workouts: list[MatchCandidate],
    ) -> MatchResult:
        best: tuple[MatchCandidate, float, str] | None = None
        for candidate in whoop_workouts:
            overlap_seconds = self._overlap_seconds(hevy_workout, candidate)
            if overlap_seconds > 0:
                confidence = min(0.99, 0.65 + min(overlap_seconds / 3600.0, 0.3))
                reason = f"time overlap {int(overlap_seconds // 60)} min"
            else:
                distance = abs(
                    (hevy_workout.started_at - candidate.started_at).total_seconds()
                )
                threshold = self.proximity_minutes * 60
                if distance > threshold:
                    continue
                confidence = max(0.35, 0.7 - (distance / threshold) * 0.25)
                reason = f"start proximity {int(distance // 60)} min"

            if best is None or confidence > best[1]:
                best = (candidate, confidence, reason)

        if best is None:
            return MatchResult(target_id=None, confidence=0.0, reason="no confident match")

        competing = [
            candidate
            for candidate in whoop_workouts
            if candidate.id != best[0].id
            and abs((candidate.started_at - hevy_workout.started_at).total_seconds())
            <= self.proximity_minutes * 60
        ]
        if competing and best[1] < 0.75:
            return MatchResult(target_id=None, confidence=best[1], reason="ambiguous candidate set")

        return MatchResult(target_id=best[0].id, confidence=best[1], reason=best[2])

    def _overlap_seconds(self, left: MatchCandidate, right: MatchCandidate) -> float:
        left_end = left.ended_at or (left.started_at + timedelta(minutes=90))
        right_end = right.ended_at or (right.started_at + timedelta(minutes=90))
        latest_start = max(left.started_at, right.started_at)
        earliest_end = min(left_end, right_end)
        return max(0.0, (earliest_end - latest_start).total_seconds())

