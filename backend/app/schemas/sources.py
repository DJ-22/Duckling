from pydantic import BaseModel


class IngestResult(BaseModel):
    source_id: str
    chunks: int
    concepts: int
    cached: bool
