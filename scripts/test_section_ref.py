"""檢查「依節號取整節」的規則能認出哪些說法。不經過 LLM、不需啟動 Ollama 或 api。

用法：
    uv run python scripts/test_section_ref.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.app.rag.chunking import load_chunks
from api.app.rag.retrieve import _SECTION_REF

# 問題 → 預期取得的節（None 代表不該觸發，改走一般檢索）
CASES = [
    ("幫我摘要 1-5 節的重點", "1-5"),
    ("整理第1-3節", "1-3"),
    ("出題 1-3 節", "1-3"),
    ("我要1-2章的摘要", "1-2"),
    ("摘要 1-3 小節", "1-3"),
    ("1-3 單元重點", "1-3"),
    ("整理 1-4 部分的重點", "1-4"),
    ("摘要 1–3 節", "1-3"),
    ("摘要 1—3 節", "1-3"),
    ("摘要 1.3 節", "1-3"),
    ("摘要 １-３ 節", "1-3"),
    ("摘要 01-03 節", "1-3"),
    ("摘要 1-3-2 節", None),  # 單一段落的 id，不是節號
    ("摘要 11-3-1 節", None),
    ("整理 1-4 的重點", None),  # 沒有單位詞：不處理
    ("算 5-3 等於多少", None),
    ("摘要移項法則那一節", None),  # 用節名稱指節：期末再處理
    ("我要第一章的摘要", None),
    ("摘要第三節", None),
]

# 認得是節號，但教材沒有這一節：取不到段落，pipeline 會改走一般檢索
NO_SUCH_SECTION = ["摘要 1-9 節", "摘要 1-33 節"]

chunks = load_chunks()
failed = 0
for query, want in CASES:
    m = _SECTION_REF.search(query)
    got = f"{int(m.group(1))}-{int(m.group(2))}" if m else None
    ok = got == want
    if ok and want:
        ok = bool([c for c in chunks if c.id.startswith(want + "-")])  # 該節確實有段落
    failed += not ok
    print(f"{'PASS' if ok else 'FAIL'}  {query}  → {got}（預期 {want}）")

for query in NO_SUCH_SECTION:
    m = _SECTION_REF.search(query)
    ok = bool(m) and not [c for c in chunks if c.id.startswith(f"{int(m.group(1))}-{int(m.group(2))}-")]
    failed += not ok
    print(f"{'PASS' if ok else 'FAIL'}  {query}  → 無此節，改走一般檢索")

total = len(CASES) + len(NO_SUCH_SECTION)
print(f"\n{total - failed}/{total} 通過")
sys.exit(1 if failed else 0)
