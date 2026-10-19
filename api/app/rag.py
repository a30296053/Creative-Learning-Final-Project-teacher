"""
此處主要實現
- 讀取教材
- 擷取ID
- 切塊
- 建立向量矩陣
"""

import os
import re
import numpy as np
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("BAAI/bge-small-zh-v1.5")

chunks = []
vecs = None

def build_index():
    """
    嘗試讀取教材，並建立RAG
    """
    global chunks, vecs

    # 資料路徑
    data_path = "../data/textbook/linear-equation.md"
    try:
        with open(data_path, 'r', encoding='utf-8') as f:
            md = f.read()

        sections, chapter, section, cur = [], None, None, None

        for line in md.splitlines():
            if line.startswith("# "):
                chapter = line[2:].strip()
            elif m := re.match(r"^## (\d+-\d+) (.+)", line):
                section, cur = f"{m[1]} {m[2]}", None
            elif line.startswith("## "):
                cur = None
            elif m := re.match(r"^### (\d+-\d+-\d+) (.+)", line):
                cur = {"id": m[1], "path": f"{chapter} > {section} > {m[2]}", "text": ""}
                sections.append(cur)
            elif cur is not None:
                cur["text"] += line + "\n"

        chunks = [{"id": s["id"], "text": f"{s['path']}\n{s['text'].strip()}"} for s in sections]
        vecs = model.encode([c["text"] for c in chunks], normalize_embeddings=True)
        print(f"共 {len(chunks)} 塊")

    except Exception as e:
        print(e)
        return 0

def retrieve_docs(query: str, k: int = 3, version: str = "A"):
    """
    根據使用者的問題進行檢索並回傳
    輸入:
        query: 問題
        k: 前k個相關的
        version: 檢索的版本
    """
    if not chunks or vecs is None:
        return []

    # 版本A: 純向量檢索(餘弦相似度)
    if version == "A":
        qv = model.encode([query], normalize_embeddings=True)[0]
        scores = vecs @ qv
        top_indices = np.argsort(-scores)[:k]

        return [chunks[i] for i in top_indices]
    # 版本B: 
    elif version == "B":
        # TODO: 檢索版本B
        pass

    return []

# 自動載入索引
build_index()