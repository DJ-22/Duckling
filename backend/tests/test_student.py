from app.services.student import comprehension_to_state


def test_low_comprehension_is_confused():
    assert comprehension_to_state(0) == "confused"
    assert comprehension_to_state(33) == "confused"


def test_mid_comprehension_is_thinking():
    assert comprehension_to_state(34) == "thinking"
    assert comprehension_to_state(66) == "thinking"


def test_high_comprehension_clicks():
    assert comprehension_to_state(67) == "clicks"
    assert comprehension_to_state(100) == "clicks"


def test_state_rises_monotonically_with_comprehension():
    order = {"confused": 0, "thinking": 1, "clicks": 2}
    seen = [order[comprehension_to_state(c)] for c in range(0, 101)]
    assert seen == sorted(seen)
