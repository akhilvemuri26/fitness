from datetime import UTC, datetime

from app.services.matching import MatchCandidate, WorkoutMatcher


def test_workout_match_prefers_overlap() -> None:
    matcher = WorkoutMatcher()
    hevy = MatchCandidate(
        id="h1",
        started_at=datetime(2026, 4, 6, 10, 0, tzinfo=UTC),
        ended_at=datetime(2026, 4, 6, 11, 0, tzinfo=UTC),
    )
    candidates = [
        MatchCandidate(
            id="w1",
            started_at=datetime(2026, 4, 6, 10, 15, tzinfo=UTC),
            ended_at=datetime(2026, 4, 6, 11, 5, tzinfo=UTC),
        ),
        MatchCandidate(
            id="w2",
            started_at=datetime(2026, 4, 6, 13, 0, tzinfo=UTC),
            ended_at=datetime(2026, 4, 6, 14, 0, tzinfo=UTC),
        ),
    ]

    result = matcher.match(hevy, candidates)

    assert result.target_id == "w1"
    assert result.confidence > 0.7


def test_workout_match_rejects_ambiguous_proximity() -> None:
    matcher = WorkoutMatcher(proximity_minutes=30)
    hevy = MatchCandidate(
        id="h1",
        started_at=datetime(2026, 4, 6, 10, 0, tzinfo=UTC),
        ended_at=datetime(2026, 4, 6, 10, 45, tzinfo=UTC),
    )
    candidates = [
        MatchCandidate(
            id="w1",
            started_at=datetime(2026, 4, 6, 10, 5, tzinfo=UTC),
            ended_at=datetime(2026, 4, 6, 10, 50, tzinfo=UTC),
        ),
        MatchCandidate(
            id="w2",
            started_at=datetime(2026, 4, 6, 10, 10, tzinfo=UTC),
            ended_at=datetime(2026, 4, 6, 10, 40, tzinfo=UTC),
        ),
    ]

    result = matcher.match(hevy, candidates)

    assert result.target_id == "w1"

