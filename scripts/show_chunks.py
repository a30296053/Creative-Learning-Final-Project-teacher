"""印出教材切塊結果，確認段落 id 與內容切得對。

用法：
    uv run python scripts/show_chunks.py          # 每塊一行摘要
    uv run python scripts/show_chunks.py -v       # 連同全文
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.app.rag.chunking import load_chunks

parser = argparse.ArgumentParser()
parser.add_argument("-v", "--verbose", action="store_true", help="印出每塊全文")
args = parser.parse_args()

chunks = load_chunks()
for c in chunks:
    print(f"[{','.join(c.ids)}] {c.title}  ({len(c.text)} 字)")
    if args.verbose:
        print(c.text, end="\n\n")
lengths = [len(c.text) for c in chunks]
print(f"\n共 {len(chunks)} 塊，長度 min={min(lengths)} max={max(lengths)}")
