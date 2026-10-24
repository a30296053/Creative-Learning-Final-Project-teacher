"""把教材依 `###` 段落 id 切塊。

基本版（RAG A）：一個 `###` 段落 = 一個切塊。
每塊都記錄涵蓋的所有段落 id（`ids`），之後改良版合併相鄰段落時，
回傳 sources 就能每個 id 各列一筆（見 spec/api-contract.md）。
"""

import re
from dataclasses import dataclass
from pathlib import Path

from ..config import DATA_DIR

# `### 1-3-3 例題：解 3x + 5 = 20` → id = 1-3-3
_SECTION = re.compile(r"^### (\d+(?:-\d+)+) (.+?)\s*$")
# `#` 或 `##` 標題會結束目前段落，避免把「本章範圍說明」併進最後一段
_HEADING = re.compile(r"^#{1,2} ")


@dataclass(frozen=True)
class Chunk:
    ids: tuple[str, ...]  # 涵蓋的段落 id
    title: str
    text: str  # 含 `###` 標題行的原文

    @property
    def id(self) -> str:
        return self.ids[0]


def chunk_markdown(markdown: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    current: tuple[str, str, list[str]] | None = None  # (id, title, lines)

    def flush() -> None:
        if current:
            sid, title, lines = current
            chunks.append(Chunk((sid,), title, "\n".join(lines).strip()))

    for line in markdown.splitlines():
        if m := _SECTION.match(line):
            flush()
            current = (m.group(1), m.group(2), [line])
        elif _HEADING.match(line):
            flush()
            current = None
        elif current:
            current[2].append(line)
    flush()
    return chunks


def load_chunks(data_dir: Path = DATA_DIR) -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in sorted((data_dir / "textbook").glob("*.md")):
        chunks += chunk_markdown(path.read_text(encoding="utf-8"))
    return chunks
