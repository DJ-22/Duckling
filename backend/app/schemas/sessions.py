from pydantic import BaseModel, Field


class StartSessionRequest(BaseModel):
    # The user's pre-explanation self-rating (how well they feel they know it).
    felt: int | None = Field(default=None, ge=0, le=100)


class TurnRequest(BaseModel):
    explanation: str = Field(min_length=1, max_length=5000)


class TurnResponse(BaseModel):
    turn_index: int
    question: str
    overall: int
    delta: int
    comprehension: int
    student_state: str
    weakest_gap: str


class SessionView(BaseModel):
    id: str
    concept_id: str
    concept_name: str
    status: str
    comprehension: int
    student_state: str
    felt: int | None
    transcript: list[dict]


class UnderstandingMapEntry(BaseModel):
    concept_id: str
    concept_name: str
    felt: int | None
    shown: int


class CompletionResult(BaseModel):
    comprehension: int
    final_overall: int
    felt: int | None
    understanding_map: list[UnderstandingMapEntry]
