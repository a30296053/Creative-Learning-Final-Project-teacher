"""基本版（RAG A）：純向量檢索，取餘弦相似度最高的 K 塊。"""

from ..config import TOP_K
from .chunking import Chunk
from .index import embed, get_index


def retrieve(query: str, k: int = TOP_K) -> list[tuple[Chunk, float]]:
    index = get_index()
    scores = index.vectors @ embed([query])[0]
    top = scores.argsort()[::-1][:k]
    return [(index.chunks[i], float(scores[i])) for i in top]
