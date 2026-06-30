from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

MIN_EASE = 1.3
DECAY_HALF_LIFE_DAYS = 14.0


@dataclass(frozen=True)
class Schedule:
    ease: float
    interval: int  # days until the next review
    next_review: datetime


def quality_from_score(overall: int) -> int:
    """Map a 0-100 grade to SM-2's 0-5 recall quality."""
    return max(0, min(5, round(overall / 20)))


def review(*, ease: float, interval: int, score: int, now: datetime | None = None) -> Schedule:
    now = now or datetime.now(timezone.utc)
    quality = quality_from_score(score)

    if quality < 3:
        # Failed recall: relearn tomorrow and nudge ease down.
        new_ease = max(MIN_EASE, ease - 0.2)
        new_interval = 1
    else:
        if interval <= 0:
            new_interval = 1
        elif interval < 6:
            new_interval = 6
        else:
            new_interval = round(interval * ease)
        new_ease = max(MIN_EASE, ease + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))

    return Schedule(round(new_ease, 2), new_interval, now + timedelta(days=new_interval))


def decay_comprehension(
    comprehension: int, next_review: datetime | None, now: datetime | None = None
) -> int:
    """Comprehension stays fresh until the review falls due, then decays with a
    half-life — so an overdue concept shows up weaker on the mastery map and
    resurfaces for review."""
    if next_review is None:
        return comprehension
    now = now or datetime.now(timezone.utc)
    overdue_days = (now - next_review).total_seconds() / 86400
    if overdue_days <= 0:
        return comprehension
    return round(comprehension * 0.5 ** (overdue_days / DECAY_HALF_LIFE_DAYS))


def compute_streak(completed_dates: list[date], today: date) -> int:
    """Consecutive days ending today (or yesterday, if today isn't practiced yet)
    that have at least one completed session."""
    days = set(completed_dates)
    cursor = today
    if cursor not in days:
        cursor = today - timedelta(days=1)
        if cursor not in days:
            return 0
    streak = 0
    while cursor in days:
        streak += 1
        cursor -= timedelta(days=1)
    return streak
