"""檢索。由 config.RAG_VERSION 切換：

- A（基本版）：純向量檢索，取餘弦相似度最高的 K 塊。
- B（改良版）：向量排名與 BM25 排名以 RRF 合併，取分數最高的 K 塊。
"""

import numpy as np

from ..config import RAG_VERSION, TOP_K
from .chunking import Chunk
from .index import embed, get_index, tokenize

RRF_K = 60  # RRF 的常用常數；越大，名次差異的影響越小


def _ranking(scores: np.ndarray, *, skip_zero: bool = False) -> list[int]:
    order = scores.argsort()[::-1]
    return [int(i) for i in order if not (skip_zero and scores[i] <= 0)]


def retrieve(
    query: str, k: int = TOP_K, version: str = RAG_VERSION
) -> list[tuple[Chunk, float]]:
    index = get_index()
    dense = index.vectors @ embed([query])[0]

    if version == "A":
        scores = dense
    elif version == "B":
        scores = np.zeros(len(index.chunks))
        # BM25 分數為 0 代表沒有任何詞重疊，不該拿名次
        bm25 = np.array(index.bm25.get_scores(tokenize(query)))
        for ranking in (_ranking(dense), _ranking(bm25, skip_zero=True)):
            for rank, i in enumerate(ranking, start=1):
                scores[i] += 1 / (RRF_K + rank)
    else:
        raise ValueError(f"未知的 RAG_VERSION：{version!r}（應為 A 或 B）")

    top = _ranking(scores)[:k]
    return [(index.chunks[i], float(scores[i])) for i in top]
