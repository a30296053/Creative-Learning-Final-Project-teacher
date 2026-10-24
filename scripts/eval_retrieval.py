"""不經過 LLM，直接評測檢索的 Top-K 命中率。

讀 jsonl 中有 `expect.sources_include` 的題目：Top-K 的切塊涵蓋的段落 id
只要包含其中一個，就算命中（與 run_tests.py 的判定相同）。

「命中」對摘要這類需要多個段落的題目太寬鬆（找到一段就過），所以另外算覆蓋率：
只看標了多個 id 的題目，覆蓋率 = 找到的標準段落數 / min(K, 標準段落數)。
分母取 K 是因為 Top-K 最多只能涵蓋 K 段。

用法：
    uv run python scripts/eval_retrieval.py
    uv run python scripts/eval_retrieval.py --k 5 tests/my_tests.jsonl
需要 Ollama 已啟動且已 pull 嵌入模型。
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.app.config import EMBED_MODEL, RAG_VERSION, TOP_K
from api.app.rag.retrieve import retrieve

parser = argparse.ArgumentParser()
parser.add_argument("file", nargs="?", default="tests/my_tests.jsonl")
parser.add_argument("--k", type=int, default=TOP_K)
parser.add_argument("--version", choices=["A", "B"], default=RAG_VERSION)
args = parser.parse_args()

with open(args.file, encoding="utf-8") as f:
    cases = [json.loads(line) for line in f if line.strip()]
cases = [c for c in cases if "sources_include" in c.get("expect", {})]

print(f"RAG {args.version}，嵌入模型 {EMBED_MODEL}，K={args.k}，共 {len(cases)} 題\n")

hit_k: dict[str, list[bool]] = defaultdict(list)
hit_1: dict[str, list[bool]] = defaultdict(list)
coverage: dict[str, list[float]] = defaultdict(list)
for case in cases:
    want = set(case["expect"]["sources_include"])
    hits = [list(c.ids) for c, _ in retrieve(case["turns"][-1], args.k, args.version)]
    ok_k = any(want & set(ids) for ids in hits)
    ok_1 = bool(want & set(hits[0]))
    for tier in (case.get("tier", "-"), "總計"):
        hit_k[tier].append(ok_k)
        hit_1[tier].append(ok_1)
    retrieved = {i for ids in hits for i in ids}
    cov = ""
    if len(want) > 1:
        c = len(want & retrieved) / min(args.k, len(want))
        for tier in (case.get("tier", "-"), "總計"):
            coverage[tier].append(c)
        cov = f"  覆蓋 {len(want & retrieved)}/{min(args.k, len(want))}"
    got = ", ".join(i for ids in hits for i in ids)
    print(
        f"{'HIT ' if ok_k else 'MISS'}  {case['id']}  應命中 {sorted(want)}  實際 [{got}]{cov}"
    )

print(f"\n{'分層':<12} {'Top-1':>8} {f'Top-{args.k}':>8} {'多段題覆蓋率':>14}")
for tier in [t for t in hit_k if t != "總計"] + ["總計"]:
    n = len(hit_k[tier])
    cov = coverage.get(tier)
    cov_text = f"{sum(cov) / len(cov):.2f} (n={len(cov)})" if cov else "-"
    print(
        f"{tier:<10} {sum(hit_1[tier]):>4}/{n:<3} {sum(hit_k[tier]):>4}/{n:<3} {cov_text:>14}"
    )
