from pydantic import BaseModel, Field


class CreateSubjectRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class SubjectInfo(BaseModel):
    id: str
    name: str
    created_at: str | None = None


class ConceptInfo(BaseModel):
    id: str
    name: str
