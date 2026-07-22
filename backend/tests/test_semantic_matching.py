from __future__ import annotations

import numpy as np

from src import semantic_matching


def test_semantic_scores_maps_embedding_scores_to_phrase_ids(monkeypatch) -> None:
    phrases = [
        {"id": "phrase:a", "text": "Ich möchte Wasser."},
        {"id": "phrase:b", "text": "Mir ist kalt."},
    ]

    monkeypatch.setattr(semantic_matching, "encode", lambda texts: np.array([[1.0, 0.0]]))
    monkeypatch.setattr(
        semantic_matching,
        "phrase_embeddings",
        lambda cache_key: np.array([[0.8, 0.2], [0.1, 0.9]]),
    )

    assert semantic_matching.semantic_scores("ich brauche wasser", phrases) == {
        "phrase:a": 0.8,
        "phrase:b": 0.1,
    }
