"""Text embeddings for policy retrieval (Q3: local all-MiniLM-L6-v2, 384 dimensions).

The model runs locally, so there is no API key and no per-call cost, and the same text always
gets the same vector. It runs on ONNX Runtime through fastembed rather than torch, so the API
fits a small server; the vectors match sentence-transformers' (cosine 1.000000 on the shipped
policies). Tests use a small deterministic fake instead of downloading the model.
"""

from functools import lru_cache
from typing import Protocol

from app.config import get_settings


class Embedder(Protocol):
    dimensions: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class LocalEmbedder:
    def __init__(self, model_name: str, dimensions: int) -> None:
        # Imported here: only ingestion and search need it. The model is downloaded once into
        # FASTEMBED_CACHE_PATH (or fastembed's default cache) and loaded from there afterwards.
        import numpy as np
        from fastembed import TextEmbedding

        self._np = np
        self.model = TextEmbedding(model_name)
        self.dimensions = dimensions
        actual = len(self.embed(["dimension check"])[0])
        if actual != dimensions:
            raise ValueError(
                f"{model_name} produces {actual}-dimensional vectors, "
                f"but EMBEDDING_DIMENSIONS is {dimensions}"
            )

    def embed(self, texts: list[str]) -> list[list[float]]:
        # Normalized, so cosine distance in pgvector equals 1 - dot product.
        vectors = self._np.array(list(self.model.embed(texts)))
        vectors = vectors / self._np.linalg.norm(vectors, axis=1, keepdims=True)
        return [vector.tolist() for vector in vectors]


@lru_cache
def get_embedder() -> Embedder:
    settings = get_settings()
    return LocalEmbedder(settings.embedding_model, settings.embedding_dimensions)


def vector_literal(vector: list[float]) -> str:
    """pgvector's text form, for `CAST(:embedding AS public.vector)`."""
    return "[" + ",".join(f"{value:.7g}" for value in vector) + "]"
