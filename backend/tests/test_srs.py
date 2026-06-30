from datetime import date, datetime, timedelta, timezone
from app import srs

NOW = datetime(2026, 6, 21, tzinfo=timezone.utc)


def test_quality_maps_score_to_zero_five():
    assert srs.quality_from_score(100) == 5
    assert srs.quality_from_score(60) == 3
    assert srs.quality_from_score(0) == 0


def test_first_successful_review_is_one_then_six_days():
    first = srs.review(ease=2.5, interval=0, score=90, now=NOW)
    assert first.interval == 1
    second = srs.review(ease=first.ease, interval=first.interval, score=90, now=NOW)
    assert second.interval == 6


def test_mature_interval_scales_by_ease():
    sched = srs.review(ease=2.5, interval=10, score=90, now=NOW)
    assert sched.interval == 25  # round(10 * 2.5)
    assert sched.next_review == NOW + timedelta(days=25)


def test_failed_recall_resets_interval_and_lowers_ease():
    sched = srs.review(ease=2.5, interval=20, score=30, now=NOW)
    assert sched.interval == 1
    assert sched.ease < 2.5


def test_ease_never_drops_below_floor():
    sched = srs.review(ease=1.3, interval=20, score=0, now=NOW)
    assert sched.ease == srs.MIN_EASE


def test_comprehension_is_fresh_until_due_then_decays():
    future = NOW + timedelta(days=5)
    assert srs.decay_comprehension(80, future, NOW) == 80
    half_life_overdue = NOW - timedelta(days=srs.DECAY_HALF_LIFE_DAYS)
    assert srs.decay_comprehension(80, half_life_overdue, NOW) == 40


def test_streak_counts_consecutive_days():
    today = date(2026, 6, 21)
    days = [today, today - timedelta(days=1), today - timedelta(days=2)]
    assert srs.compute_streak(days, today) == 3


def test_streak_breaks_on_gap():
    today = date(2026, 6, 21)
    days = [today, today - timedelta(days=2)]  # missed yesterday
    assert srs.compute_streak(days, today) == 1


def test_streak_survives_if_today_not_yet_practiced():
    today = date(2026, 6, 21)
    days = [today - timedelta(days=1), today - timedelta(days=2)]
    assert srs.compute_streak(days, today) == 2
