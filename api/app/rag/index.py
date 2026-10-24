"""建立教材切塊的記憶體索引（不寫檔案、不用向量資料庫）。

兩種索引：Ollama 嵌入的向量（A、B 都用），以及 BM25 關鍵詞索引（只有 B 用）。
"""

import re
from dataclasses import dataclass
from functools import lru_cache

import httpx
import numpy as np
from rank_bm25 import BM25Okapi

from ..config import EMBED_MODEL, OLLAMA_URL
from .chunking import Chunk, load_chunks


@dataclass(frozen=True)
class Index:
    chunks: list[Chunk]
    vectors: np.ndarray  # (n, dim)，每列已正規化，內積 = 餘弦相似度
    bm25: BM25Okapi


_TOKEN = re.compile(r"[A-Za-z0-9]+|[\u4e00-\u9fff]+")


def tokenize(text: str) -> list[str]:
    """英數連續字串為一個詞；中文連續字串切成相鄰兩字（單字則保留單字）。

    不用斷詞套件：教材是數學課文，詞彙固定且短，雙字切法夠用，也不多一個依賴。
    """
    tokens: list[str] = []
    for run in _TOKEN.findall(text.lower()):
        if run.isascii() or len(run) == 1:
            tokens.append(run)
        else:
            tokens += [run[i : i + 2] for i in range(len(run) - 1)]
    return tokens


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
    return Index(
        chunks,
        embed([c.text for c in chunks]),
        BM25Okapi([tokenize(c.text) for c in chunks]),
    )
