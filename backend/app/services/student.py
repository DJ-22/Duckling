from __future__ import annotations
from typing import Literal

StudentState = Literal["confused", "thinking", "clicks"]

# Comprehension (0-100) maps to the three visible expression states the character
# stub renders. Kept server-side so the persona's growth is consistent everywhere
# it's shown and can be asserted in tests without the frontend.
_THINKING_AT = 34
_CLICKS_AT = 67


def comprehension_to_state(comprehension: int) -> StudentState:
    if comprehension >= _CLICKS_AT:
        return "clicks"
    if comprehension >= _THINKING_AT:
        return "thinking"
    return "confused"
