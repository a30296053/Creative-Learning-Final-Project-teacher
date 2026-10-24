"""用 Ollama 嵌入教材切塊，建立記憶體索引（不寫檔案、不用向量資料庫）。"""

from dataclasses import dataclass
from functools import lru_cache

import httpx
import numpy as np

from ..config import EMBED_MODEL, OLLAMA_URL
from .chunking import Chunk, load_chunks


@dataclass(frozen=True)
class Index:
    chunks: list[Chunk]
    vectors: np.ndarray  # (n, dim)，每列已正規化，內積 = 餘弦相似度


def embed(texts: list[str]) -> np.ndarray:
    resp = httpx.post(
        f"{OLLAMA_URL}/api/embed",
        json={"model": EMBED_MODEL, "input": texts},
        timeout=120,
    )
    resp.raise_for_status()
    vectors = np.array(resp.json()["embeddings"], dtype=np.float32)
    return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)


@lru_cache(maxsize=1)
def get_index() -> Index:
    """第一次呼叫時建立，之後重複使用。"""
    chunks = load_chunks()
    return Index(chunks, embed([c.text for c in chunks]))
