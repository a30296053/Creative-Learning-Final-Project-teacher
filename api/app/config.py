"""所有可調整的設定集中在這裡，其他檔案一律 `from .config import ...`。

預設值 = 不做任何設定、直接 `uv run` 就能運作的值。
- Docker 專用的值（OLLAMA_URL、DATA_DIR）由 docker-compose.yml 的 environment 覆蓋。
- 祕密與個人偏好（CLOUD_API_KEY、想換的 LOCAL_MODEL）放 .env，見 .env.example。
會影響結果的設定（之後的 TOP_K、RAG_VERSION 等）請把預設值寫在這裡，讓 git 記錄下來。
"""

import os
from pathlib import Path

# 地端模型（Ollama）。容器內的 localhost 是容器自己，所以 Docker 裡要改成 host.docker.internal
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
LOCAL_MODEL = os.environ.get("LOCAL_MODEL", "qwen2.5:3b")
# 低溫度讓回答緊貼參考資料，也讓同一題的結果比較穩定
LLM_TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0.2"))

# 教材資料夾。預設是 repo 根目錄的 data/；Docker 裡 compose 會掛載到 /data
DATA_DIR = Path(
    os.environ.get("DATA_DIR") or Path(__file__).resolve().parents[2] / "data"
)

# 雲端 LLM 的 key（尚未使用）。只能放 .env，不可寫進程式碼
CLOUD_API_KEY = os.environ.get("CLOUD_API_KEY", "")

# RAG。這兩個會影響報告數字，預設值要 commit，不要只放在自己的 .env
EMBED_MODEL = os.environ.get("EMBED_MODEL", "bge-m3")  # 走 Ollama，需先 ollama pull
TOP_K = int(os.environ.get("TOP_K", "3"))
# "A" = 純向量檢索（基本版）；"B" = 向量 + BM25，以 RRF 合併（改良版）
RAG_VERSION = os.environ.get("RAG_VERSION", "A")
