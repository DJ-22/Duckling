from pydantic import BaseModel, Field, field_validator


class CoveragePoint(BaseModel):
    point: str
    covered: bool


class CorrectnessClaim(BaseModel):
    claim: str
    contradicts_source: bool


class GradeResult(BaseModel):
    """Validated grader output. The raw model response is untrusted: out-of-range
    numbers are clamped here and only these fields are ever consumed downstream,
    so a manipulated grade can never become anything but a bounded score."""

    coverage: list[CoveragePoint] = Field(default_factory=list)
    correctness: list[CorrectnessClaim] = Field(default_factory=list)
    misconceptions_hit: list[str] = Field(default_factory=list)
    recitation_score: float = 0.0
    overall: int = 0
    weakest_gap: str = ""
    student_comprehension_delta: int = 0

    @field_validator("recitation_score", mode="before")
    @classmethod
    def _clamp_recitation(cls, v: object) -> float:
        try:
            return min(1.0, max(0.0, float(v)))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return 0.0

    @field_validator("overall", mode="before")
    @classmethod
    def _clamp_overall(cls, v: object) -> int:
        try:
            return min(100, max(0, round(float(v))))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return 0

    @field_validator("student_comprehension_delta", mode="before")
    @classmethod
    def _clamp_delta(cls, v: object) -> int:
        try:
            return min(20, max(0, round(float(v))))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return 0
