from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

import numpy as np

MODEL_NAME = "Xenova/paraphrase-multilingual-MiniLM-L12-v2"
ONNX_FILE = "onnx/model_quantized.onnx"
TOKENIZER_FILE = "tokenizer.json"


@lru_cache(maxsize=1)
def model_files() -> tuple[Path, Path]:
    from huggingface_hub import hf_hub_download

    model_path = hf_hub_download(MODEL_NAME, ONNX_FILE)
    tokenizer_path = hf_hub_download(MODEL_NAME, TOKENIZER_FILE)
    return Path(model_path), Path(tokenizer_path)


@lru_cache(maxsize=1)
def tokenizer():
    from tokenizers import Tokenizer

    _, tokenizer_path = model_files()
    return Tokenizer.from_file(str(tokenizer_path))


@lru_cache(maxsize=1)
def session():
    import onnxruntime as ort

    model_path, _ = model_files()
    return ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])


@lru_cache(maxsize=32)
def phrase_embeddings(cache_key: tuple[tuple[int, str], ...]):
    phrases = [text for _, text in cache_key]
    return encode(phrases)


def encode(texts: list[str]):
    encoded = tokenizer().encode_batch(texts)
    max_length = max(len(item.ids) for item in encoded)
    input_ids = np.array([pad(item.ids, max_length) for item in encoded], dtype=np.int64)
    attention_mask = np.array([pad(item.attention_mask, max_length) for item in encoded], dtype=np.int64)
    token_type_ids = np.array([pad(item.type_ids, max_length) for item in encoded], dtype=np.int64)
    outputs = session().run(
        None,
        {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "token_type_ids": token_type_ids,
        },
    )
    embeddings = mean_pool(outputs[0], attention_mask)
    return normalize(embeddings)


def pad(values: list[int], length: int):
    return values + [0] * (length - len(values))


def mean_pool(token_embeddings, attention_mask):
    mask = np.expand_dims(attention_mask, axis=-1)
    return (token_embeddings * mask).sum(axis=1) / np.maximum(mask.sum(axis=1), 1)


def normalize(embeddings):
    return embeddings / np.maximum(np.linalg.norm(embeddings, axis=1, keepdims=True), 1e-12)


def semantic_scores(text: str, phrases: Sequence[dict]) -> dict[str, float]:
    cache_key = tuple((str(phrase["id"]), phrase.get("text", "")) for phrase in phrases)
    if not cache_key:
        return {}

    query_embedding = encode([text])[0]
    scores = phrase_embeddings(cache_key) @ query_embedding
    return {phrase_id: float(score) for (phrase_id, _), score in zip(cache_key, scores, strict=True)}
