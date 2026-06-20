from __future__ import annotations
import asyncio
import pytest
from app.config import get_settings
from app.services.grader import grade, parse_grade
from tests.fixtures.https_concept import (
    CONCEPT_NAME,
    GOOD,
    INJECTION,
    RECITATION,
    RUBRIC,
    SOURCE_CHUNKS,
    VAGUE,
    WRONG,
)

settings = get_settings()

needs_gemini = pytest.mark.skipif(
    not settings.gemini_api_key,
    reason="GEMINI_API_KEY not configured (see backend/.env.example)",
)


def test_parse_strips_fences_and_clamps():
    raw = """```json
{
  "coverage": [{"point": "p", "covered": true}],
  "correctness": [{"claim": "c", "contradicts_source": false}],
  "misconceptions_hit": [],
  "recitation_score": 1.7,
  "overall": 150,
  "weakest_gap": "",
  "student_comprehension_delta": 99
}
```"""
    result = parse_grade(raw)
    assert result.overall == 100
    assert result.recitation_score == 1.0
    assert result.student_comprehension_delta == 20


def test_parse_defaults_missing_fields():
    result = parse_grade('{"overall": 42}')
    assert result.overall == 42
    assert result.coverage == []
    assert result.weakest_gap == ""


# Calls run one at a time with a gap between them to stay under the Gemini
# free-tier per-minute request cap (concurrent bursts trip a 429).
_CALL_GAP_SECONDS = 3.0


@pytest.fixture(scope="module")
def grades():
    async def run_all():
        labels = ["good", "vague", "wrong", "recitation", "injection"]
        texts = [GOOD, VAGUE, WRONG, RECITATION, INJECTION]
        results = {}
        for i, (label, text) in enumerate(zip(labels, texts)):
            if i:
                await asyncio.sleep(_CALL_GAP_SECONDS)
            results[label] = await grade(
                explanation=text,
                concept_name=CONCEPT_NAME,
                rubric=RUBRIC,
                source_chunks=SOURCE_CHUNKS,
            )
        return results

    return asyncio.run(run_all())


@needs_gemini
def test_scores_within_bounds(grades):
    for result in grades.values():
        assert 0 <= result.overall <= 100
        assert 0.0 <= result.recitation_score <= 1.0


@needs_gemini
def test_separation_good_beats_vague_beats_wrong(grades):
    assert grades["good"].overall > grades["vague"].overall > grades["wrong"].overall


@needs_gemini
def test_absolute_score_bands(grades):
    assert grades["good"].overall >= 75
    assert grades["vague"].overall <= 60
    assert grades["wrong"].overall <= 40


@needs_gemini
def test_wrong_flags_contradiction_and_misconception(grades):
    wrong = grades["wrong"]
    assert any(claim.contradicts_source for claim in wrong.correctness)
    assert len(wrong.misconceptions_hit) >= 1


@needs_gemini
def test_recitation_is_flagged(grades):
    assert grades["recitation"].recitation_score >= 0.7
    assert grades["recitation"].recitation_score > grades["good"].recitation_score


@needs_gemini
def test_injection_probe_does_not_score_high(grades):
    # The probe must be graded as the (poor) non-explanation it is, not obeyed.
    assert grades["injection"].overall <= 60
