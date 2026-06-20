from pydantic import BaseModel, Field


class ConceptRubric(BaseModel):
    points: list[str] = Field(default_factory=list)
    causal_links: list[str] = Field(default_factory=list)
    misconceptions: list[str] = Field(default_factory=list)


class ExtractedConcept(BaseModel):
    name: str
    rubric: ConceptRubric = Field(default_factory=ConceptRubric)


class Extraction(BaseModel):
    concepts: list[ExtractedConcept] = Field(default_factory=list)
