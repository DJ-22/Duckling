from __future__ import annotations
from functools import lru_cache
from sentence_transformers import SentenceTransformer

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384  # must match the chunks.embedding vector(384) column


@lru_cache(maxsize=1)
def _model() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)


def embed_texts(texts: list[str]) -> list[list[float]]:
    # normalize_embeddings so cosine similarity matches the pgvector `<=>` query
    # used at retrieval time.
    vectors = _model().encode(texts, normalize_embeddings=True)
    return [vector.tolist() for vector in vectors]


def embed_text(text: str) -> list[float]:
    return embed_texts([text])[0]
