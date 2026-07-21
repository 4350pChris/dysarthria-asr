from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


@lru_cache(maxsize=1)
def model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(MODEL_NAME)


@lru_cache(maxsize=32)
def phrase_embeddings(cache_key: tuple[tuple[int, str], ...]):
    phrases = [text for _, text in cache_key]
    return model().encode(phrases, normalize_embeddings=True)


def semantic_scores(text: str, phrases: Sequence[dict]) -> dict[int, float]:
    cache_key = tuple((phrase["id"], phrase.get("text", "")) for phrase in phrases)
    if not cache_key:
        return {}

    query_embedding = model().encode([text], normalize_embeddings=True)[0]
    scores = phrase_embeddings(cache_key) @ query_embedding
    return {phrase_id: float(score) for (phrase_id, _), score in zip(cache_key, scores, strict=True)}
