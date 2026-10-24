"""檢索。由 config.RAG_VERSION 切換：

- A（基本版）：純向量檢索，取餘弦相似度最高的 K 塊。
- B（改良版）：切塊的索引文字加上節標題，向量排名與 BM25 排名以 RRF 合併，取分數最高的 K 塊；
  若向量檢索的第 1 名沒有進入 Top-K，用它取代最後一塊。
"""

import re

import numpy as np

from ..config import RAG_VERSION, TOP_K
from .chunking import Chunk
from .index import embed, get_index, tokenize

# 「摘要 1-3 節」這類明確的節號：切塊內容裡沒有節標題可比對，直接依段落 id 前綴取整節
_SECTION_REF = re.compile(r"(?<![\d-])(\d+-\d+)\s*節")

RRF_K = 60  # RRF 的常用常數；越大，名次差異的影響越小


def _ranking(scores: np.ndarray, *, skip_zero: bool = False) -> list[int]:
    order = scores.argsort()[::-1]
    return [int(i) for i in order if not (skip_zero and scores[i] <= 0)]


def retrieve(
    query: str, k: int = TOP_K, version: str = RAG_VERSION
) -> list[tuple[Chunk, float]]:
    index = get_index(with_section=version == "B")
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
    if version == "B" and k > 1:
        # BM25 只能比對字面，通用詞（如「方程式」）會把它帶偏；向量檢索的第 1 名不該因此被擠出 Top-K
        best_dense = _ranking(dense)[0]
        if best_dense not in top:
            top = top[: k - 1] + [best_dense]
    return [(index.chunks[i], float(scores[i])) for i in top]


def section_chunks(query: str) -> list[Chunk]:
    """問題中提到「N-N 節」時，回傳該節所有切塊；沒提到或查無此節則回傳空 list。"""
    m = _SECTION_REF.search(query)
    if not m:
        return []
    prefix = m.group(1) + "-"
    return [c for c in get_index().chunks if c.id.startswith(prefix)]
