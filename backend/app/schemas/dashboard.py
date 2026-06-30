from pydantic import BaseModel
from .subjects import SubjectInfo


class MasteryEntry(BaseModel):
    concept_id: str
    concept_name: str
    subject_id: str | None
    comprehension: int
    next_review: str | None


class InProgressSession(BaseModel):
    id: str
    concept_id: str
    concept_name: str
    updated_at: str | None


class Dashboard(BaseModel):
    subjects: list[SubjectInfo]
    mastery: list[MasteryEntry]
    due: list[MasteryEntry]
    in_progress: list[InProgressSession]
    streak: int
