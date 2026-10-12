# 開發筆記（組員接手用）

角色：教師 AI 助教。這份是「相對於助教模板，我們改了什麼、怎麼開發」，規格請看 `spec/`。

## 1. 相對模板改了什麼

| 項目       | 模板                                          | 現在                                                                 |
| ------------ | ----------------------------------------------- | ---------------------------------------------------------------------- |
| 套件管理   | `api/requirements.txt`、`ui/requirements.txt` | 根目錄`pyproject.toml` + `uv.lock`，依賴分 `api`、`ui` 兩個 group    |
| Dockerfile | `pip install -r requirements.txt`             | `uv sync --locked --only-group <group>`（api 或 ui），build context 為 repo 根目錄 |
| 設定       | `pipeline.py` 內 `os.environ.get`             | 集中在`api/app/config.py`                                            |
| `.env`     | compose 必須有                                | 選用（驗收機不會有）；只放祕密與個人偏好                             |
| Python     | 無限制                                        | 固定 3.12（`.python-version`，與 `python:3.12-slim` 一致）           |

## 2. 一次說清楚：有哪些東西在跑

```text
Ollama :11434  ◀── OLLAMA_URL ── 後端 api :8000  ◀── API_URL ── 前端 ui :8501
（模型伺服器）                 （FastAPI，所有邏輯）            （Streamlit，只負責顯示）
```

- 開發時三個都直接跑在你的環境裡（`uv run`），**不需要 Docker**。
- 驗收時助教用 `docker compose up`，api、ui 各裝進一個容器；**Ollama 裝在主機，不在 Docker 裡**。
- 助教的自動測試只打 `localhost:8000/chat`，不經過 ui。

## 3. 第一次安裝

```bash
# 1. uv（https://docs.astral.sh/uv/getting-started/installation/）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Ollama（https://ollama.com/download），然後下載模型（約 2 GB）
ollama pull qwen2.5:3b
ollama run qwen2.5:3b "你好"        # 測試

# 3. 專案環境（會依 uv.lock 建立 .venv，自動使用 Python 3.12）
uv sync
```

不需要建立 `.env`。程式內的預設值就能直接跑。

## 4. 日常開發（`uv run`）

開三個終端機（或背景執行），從 repo 根目錄：

```bash
ollama serve                                                   # 若 Ollama 沒在背景跑
uv run uvicorn app.main:app --app-dir api --reload             # 後端 http://localhost:8000/docs
uv run streamlit run ui/app.py                                 # 前端 http://localhost:8501
```

測試：

```bash
uv run python scripts/run_tests.py tests/my_tests.jsonl        # 自訂題
uv run python scripts/run_tests.py tests/teacher.jsonl         # 公開題（期中不計分，但報告要附）
curl -s localhost:8000/health
```

`--reload` 與 Streamlit 都會在存檔時自動重載；改了 `config.py` 或環境變數則需重啟後端。

### 新增套件

```bash
uv add --group api <套件>      # 後端用
uv add --group ui <套件>       # 前端用
```

會同步更新 `pyproject.toml` 與 `uv.lock`，**兩個都要 commit**。不要手動 `pip install`。

## 5. 設定放哪裡

| 設定                       | 放哪裡                                           | 例子                                        |
| ---------------------------- | -------------------------------------------------- | --------------------------------------------- |
| 每個人都該一致、會影響結果 | `api/app/config.py` 的預設值（會 commit）        | `TOP_K`、`RAG_VERSION`、`CHUNK_SIZE`        |
| 只有在 Docker 裡才需要改   | `docker-compose.yml` 的 `environment`            | `OLLAMA_URL`、`DATA_DIR`                    |
| 祕密或個人偏好             | `.env`（**不可 commit**，範本見 `.env.example`） | `CLOUD_API_KEY`、電腦較弱時的 `LOCAL_MODEL` |

規則：

- 專案必須在**沒有 `.env`、沒有雲端 key** 時也能以純地端模式完整運作。
- 會影響報告數字的設定不要只放在自己的 `.env`，否則別人重現不了。
- `uv run` 不會自動讀 `.env`；要用時：`uv run --env-file .env uvicorn app.main:app --app-dir api --reload`。
- 換地端模型要先 `ollama pull <模型>`（Ollama 的 API 不會自動下載，找不到會回 404），驗收機也必須有該模型，並寫進 README。

## 6. 用 Docker 驗證（繳交前、改了 Dockerfile 或依賴後）

```bash
docker compose up --build        # 建置並啟動 api、ui
curl -s localhost:8000/health    # 預期 {"status":"ok"}
docker compose down
```

- 容器內連主機上的 Ollama 用 `host.docker.internal`。Linux 主機的 Ollama 需對容器開放：`OLLAMA_HOST=0.0.0.0`（見 README 疑難排解）。
- 容器內的程式碼是 build 時複製進去的，改了程式要重新 `--build`。
- ⚠️ **目前 Docker 建置尚未實際驗證**（開發環境沒有 Docker），期中前務必在有 Docker 的機器上跑一次。

## 7. 檔案架構

```text
.
├── pyproject.toml, uv.lock, .python-version   # 唯一的依賴與 Python 版本來源
├── docker-compose.yml, .dockerignore
├── api/
│   ├── Dockerfile
│   └── app/
│       ├── main.py        # /health、/chat 端點（不用動）
│       ├── schemas.py     # 回傳格式（欄位名稱不可改）
│       ├── config.py      # 所有設定與預設值
│       └── pipeline.py    # 主要實作位置（RAG、護欄、生成都從這裡展開）
├── ui/
│   ├── Dockerfile
│   └── app.py             # Streamlit 介面
├── data/                  # 助教提供的教材，容器內為 /data
├── tests/                 # 公開題與自訂題（jsonl）
├── scripts/run_tests.py   # 測試程式（只用標準庫）
├── spec/                  # 助教規格（期中、API 契約、UI、期末驗收）
└── docs/
    ├── midterm-report.md  # 期中報告
    └── dev-note.md        # 本文件
```

## 8. 期中待辦（11/1 23:59，詳見 `spec/midterm.md`）

- [ ]  RAG：切塊（每個 chunk 記錄涵蓋的所有段落 id）、嵌入與索引、檢索、生成，`sources[].id` 用段落 id
- [ ]  兩個版本（基本版、改良版），可用設定切換（建議 `RAG_VERSION=A|B`）
- [ ]  教師情境至少一個可完整執行（摘要或教材問答）
- [ ]  自訂評測集 ≥ 10 題，記錄兩版 Top-K 命中與命中率
- [ ]  失敗案例 ≥ 2 個（含假設與驗證方式）
- [ ]  跑 `tests/teacher.jsonl` 並附輸出
- [ ]  `docs/midterm-report.md`，含 AI 使用揭露
- [ ]  README 註明使用的模型（含嵌入模型）；在 Docker 驗證 `docker compose up`
- [ ]  `git tag midterm && git push origin midterm`，並到繳交表填 repo 連結

## 9. 協作約定

- 各自用自己的帳號 commit（個人貢獻依 commit 紀錄評估）。
- 目前開發分支：`dev/wang`。
- `.env`、API key 絕不 commit；曾 push 過就立刻到服務商撤銷。
