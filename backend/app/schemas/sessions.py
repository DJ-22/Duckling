from pydantic import BaseModel, Field


class TurnRequest(BaseModel):
    explanation: str = Field(min_length=1, max_length=5000)


class TurnResponse(BaseModel):
    turn_index: int
    question: str
    overall: int
    delta: int
    comprehension: int
    weakest_gap: str


class SessionView(BaseModel):
    id: str
    concept_id: str
    concept_name: str
    status: str
    comprehension: int
    transcript: list[dict]


class CompletionResult(BaseModel):
    comprehension: int
    final_overall: int
