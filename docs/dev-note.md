# 開發筆記（教師 AI 助教組）

README 是助教給的通用說明；這份是**我們這組的精簡版**：現在的架構、開發原則、接下來怎麼做。十分鐘內看完即可接手。規格請看 `spec/`。

## 1. 一分鐘總覽

教師 AI 助教：依教材（`data/textbook/`）做 RAG。**期中已完成問答與摘要**；出題（含 Fact Critic 查核）與護欄是期末範圍。

```mermaid
flowchart LR
    B[瀏覽器] -->|:8501| UI[ui<br/>Streamlit<br/>只負責顯示]
    T[助教測試腳本] -->|POST /chat :8000| API
    UI -->|POST /chat| API[api<br/>FastAPI<br/>所有邏輯]
    API -->|:11434| O[(Ollama<br/>主機上)]
    D[/data 教材/] -.唯讀.-> API
```

- **ui 沒有任何邏輯**，只呼叫 `/chat`。助教的自動測試直接打 api，不經過 ui。
- **Ollama 裝在主機，不在 Docker 裡**（課程規定）。我們用兩個模型：生成 `qwen2.5:3b`、嵌入 `bge-m3`，驗收機都要先 `ollama pull`。
- 兩種執行方式，程式碼相同，差別只在環境：


|             | 開發（日常）       | 驗證（繳交前）                               |
| ------------- | -------------------- | ---------------------------------------------- |
| 指令        | `uv run ...`       | `docker compose up --build`                  |
| 用途        | 改程式、馬上看結果 | 確認驗收機上也能跑                           |
| Ollama 位址 | `localhost:11434`  | `host.docker.internal:11434`（compose 設定） |

## 2. 快速開始

```bash
# 一次性：uv（https://docs.astral.sh/uv/getting-started/installation/）與 Ollama（https://ollama.com/download）
ollama pull qwen2.5:3b          # 約 2 GB，生成
ollama pull bge-m3              # 約 1.2 GB，嵌入（RAG 檢索必要）
uv sync                         # 依 uv.lock 建 .venv（Python 3.12）

# 日常：開兩個終端機，在 repo 根目錄
uv run uvicorn api.app.main:app --reload    # 後端 http://localhost:8000/docs
uv run streamlit run ui/app.py              # 前端 http://localhost:8501

# 測試（run_tests.py 需要 api 已啟動）
uv run python scripts/run_tests.py tests/teacher.jsonl     # 助教公開題；出題、護欄尚未實作，期中預期 3/12（摘要 3 題全過）
uv run python scripts/run_tests.py tests/my_tests.jsonl    # 自訂 30 題，同樣含出題與範圍外題，那兩類在期末功能完成前會失敗
uv run python scripts/eval_retrieval.py --version B        # 只測檢索命中率（不經 LLM、不需啟動 api），--version A|B、--k N
uv run python scripts/show_chunks.py -v                    # 印出切塊結果，確認段落 id 切得對
```

切換檢索版本：`RAG_VERSION=A uv run uvicorn api.app.main:app --reload`（預設 B）。環境變數可直接寫在指令前；Docker 則在 `.env` 加一行 `RAG_VERSION=A`。

不需要 `.env`。新增套件：`uv add --group api <套件>`（前端用 `--group ui`），`pyproject.toml` 與 `uv.lock` **都要 commit**，不要手動 `pip install`。

## 3. 開發原則

1. **純地端可完整運作**：沒有 `.env`、沒有雲端 key 也能跑。雲端只是選用路徑，`route` 欄位要如實回報。
2. **`/chat` 格式不可改**：欄位以 `spec/api-contract.md` 為準，`schemas.py` 只增不改。
3. **設定集中在 `api/app/config.py`**，其他檔案只 `from .config import ...`，不要散落 `os.environ`。
4. **會影響報告數字的設定（`TOP_K`、`RAG_VERSION`、`EMBED_MODEL`、`LLM_TEMPERATURE`）預設值寫進 `config.py` 並 commit**，不要只放在自己的 `.env`，否則別人重現不了。
5. **所有後端程式碼放在 `api/app/` 底下**：Dockerfile 只複製這個資料夾，放在別處的程式不會進容器。
6. **依賴只有一個來源**：`pyproject.toml` + `uv.lock`。嵌入走 Ollama，**不要引入 PyTorch／sentence-transformers**（image 會膨脹到數 GB，拖慢 10 分鐘內可用的限制）。
7. **先在本機跑通，再用 Docker 驗證**。Docker 出現的錯誤才是 Docker 的問題。
8. **`.env`、API key 絕不 commit**；曾 push 過就立刻到服務商撤銷。

### 設定放哪裡


| 設定                     | 放哪裡                                   | 例子                           |
| -------------------------- | ------------------------------------------ | -------------------------------- |
| 每個人都該一致、影響結果 | `config.py` 預設值（commit）             | `TOP_K`、`RAG_VERSION`、`EMBED_MODEL` |
| 只有 Docker 裡才不同     | `docker-compose.yml` 的 `environment`    | `OLLAMA_URL`、`DATA_DIR`       |
| 祕密或個人偏好           | `.env`（不 commit，範本 `.env.example`） | `CLOUD_API_KEY`、`LOCAL_MODEL` |

`uv run` 不會自動讀 `.env`，要用時加 `--env-file .env`。換地端模型要先 `ollama pull`，驗收機也要有，並寫進 README。

## 4. 後端架構

### 現況

```text
.
├── pyproject.toml, uv.lock, .python-version   # 依賴與 Python 版本的唯一來源
├── docker-compose.yml, .dockerignore
├── api/
│   ├── Dockerfile
│   └── app/
│       ├── main.py        # /health、/chat（不用動）
│       ├── schemas.py     # 回傳格式（欄位名稱不可改）
│       ├── config.py      # 所有設定
│       ├── pipeline.py    # 流程調度：問題含「N-N 節」就取整節，否則檢索 → 組 prompt → 呼叫 Ollama（護欄目前固定 pass）
│       └── rag/
│           ├── chunking.py  # 依 ### 段落 id 切塊，記錄所屬 ## 節標題
│           ├── index.py     # Ollama 嵌入 + BM25，建立記憶體索引
│           └── retrieve.py  # 版本 A／B（RAG_VERSION）與 section_chunks（取整節）
├── ui/{Dockerfile, app.py}
├── data/                  # 助教教材（容器內為唯讀的 /data）
├── tests/                 # teacher.jsonl（助教公開題）、my_tests.jsonl（自訂 30 題）
├── scripts/               # run_tests.py（打 /chat）、eval_retrieval.py（只測檢索）、show_chunks.py
├── spec/                  # 助教規格
└── docs/{dev-note.md, midterm-report.md}
```

### 規劃（尚未建檔的部分；實作時再建，不要預先建空檔案）

教師組的功能很多，全塞進 `pipeline.py` 會變成難以分工的大檔案。`pipeline.py` 只保留**流程調度**，功能拆到各模組。期末要新增的模組如下（`rag/` 已完成，列出來是為了看整體）：

```text
api/app/
├── pipeline.py            # 調度：決定走哪條路、串起下面的模組
├── llm.py                 # 呼叫 Ollama／雲端，集中處理 route
├── guardrail.py           # out_of_scope 判斷
├── rag/
│   ├── chunking.py        # 已完成
│   ├── index.py           # 已完成
│   └── retrieve.py        # 已完成
└── teacher/
    ├── questions.py       # 出題
    └── critic.py          # Fact Critic（期末）
```

```mermaid
flowchart TD
    Q[POST /chat] --> G{guardrail<br/>是否超出教材}
    G -->|out_of_scope| R[refuse]
    G -->|pass| I{意圖}
    I -->|問答／摘要| RT[retrieve<br/>RAG_VERSION = A / B]
    I -->|出題| RT
    RT --> GEN[llm 生成]
    GEN -->|出題| C[Fact Critic<br/>只留 pass 的題目]
    GEN -->|問答／摘要| A[ChatResponse + sources]
    C --> A
    R --> A
```

上圖是**期末目標**流程。期中已實作的是「檢索 → 生成」；另外在檢索之前有一條規則：問題含「N-N 節」就直接取該節所有段落。

版本 A（純向量）與 B（節標題 + 向量 + BM25 以 RRF 合併，並保證向量第 1 名進入 Top-K）各自獨立、由 `RAG_VERSION` 切換（預設 B），才能公平比較命中率（期中 30 分的部分）。成績與取捨見 `docs/midterm-report.md` 第 3～5 節。

### RAG 索引的存放（已決定）

教材很小（`data/textbook/` 目前只有 `linear-equation.md`，切成 21 塊），因此：

- **索引放記憶體**（`numpy` 向量 + `rank_bm25`），第一次請求時用 Ollama 嵌入後建立，**不寫檔案、不用向量資料庫**。
- 若日後真的需要快取到磁碟，用**具名 volume** 掛到 `/cache`，並在 Dockerfile 先 `mkdir /cache && chown nonroot /cache`（見第 6 節的實測）。**不要寫進 `/app`**。
- 目前索引在第一次請求時才建（約數秒），不影響 `healthcheck.start_period`（10 秒）；若改成啟動時就建，要同步延長它。

## 5. 期中進度（11/1 23:59，詳見 `spec/midterm.md`）

建議順序，每步都能獨立驗證：

- [X]  1. `rag/chunking.py` + 小腳本印出每個 chunk 的段落 id，確認切得對
- [X]  2. `rag/index.py`、`rag/retrieve.py` 基本版 A，打通 `/chat` 並回傳 `sources[].id`
- [X]  3. 自訂評測集 ≥ 10 題（現有 30 題，句型比照 `teacher.jsonl`；其中 24 題標有應命中的段落 id，可評檢索，6 題範圍外題留給護欄）
- [X]  4. `scripts/eval_retrieval.py`：自動算兩版 Top-K 命中率
- [X]  5. 改良版 B（更換切塊、混合檢索或重排序），用數據比較
- [X]  6. 至少一個教師情境完整可用（摘要或教材問答）
- [X]  7. 失敗案例 ≥ 2 個、跑 `tests/teacher.jsonl` 並附輸出、`docs/midterm-report.md`（含 AI 使用揭露）
- [ ]  8. README 註明模型（含嵌入模型，已完成）；`docker compose up --build` 完整驗證（繳交前最後再跑一次）
- [ ]  9. `git tag midterm && git push origin midterm`，填繳交表

不在期中範圍：護欄（`guardrail` 欄位需存在，可固定 `pass`）、Fact Critic、Agent。

## 6. Docker 筆記

```bash
docker compose up --build        # 建置並啟動
curl -s localhost:8000/health    # 預期 {"status":"ok"}
docker compose down
```

**何時要 `--build`**：改了程式、`pyproject.toml`、`uv.lock`、Dockerfile。只改 `docker-compose.yml` 設定或 `data/` 教材則不用（教材是掛載的）。

**設計重點**

- 基底 `python:3.12-slim-trixie`（固定 Debian 版本，避免悄悄升級）；`uv` 固定版本複製進來。
- 依賴安裝用 bind mount（`uv.lock`、`pyproject.toml`、`.python-version`）加 cache mount，最終 image 不殘留這些檔案；`--only-group` 讓 api 與 ui 各自只裝需要的套件。
- 執行用 `PATH=/app/.venv/bin`，不用 `uv run`（`uv run` 啟動時會同步所有預設 group）。
- ui 等 api 通過 `/health` 健康檢查才啟動（`depends_on: service_healthy`）。
- 容器連主機 Ollama：`extra_hosts: host.docker.internal:host-gateway` 只解決名稱；**Linux 還需要 Ollama 監聽 `0.0.0.0`**（`OLLAMA_HOST=0.0.0.0`，見 README 疑難排解）。

**注意事項**

- **port 只綁 `127.0.0.1`**。Docker 發佈的 port 會繞過 ufw，綁全部介面會讓實驗室伺服器上的 api 暴露在外網。助教與組員在自己電腦用 `localhost` 不受影響；在伺服器上開發則用 VS Code 轉發或 `ssh -L 8501:localhost:8501`。
- **compose 與 `uv run` 不能同時跑**：兩者都用 8000，後啟動的會 `address already in use`。
- **容器以非 root 使用者（`nonroot`，uid 999）執行**。實測的寫入規則：


| 寫入位置                                 | 結果                        |
| ------------------------------------------ | ----------------------------- |
| `/app`                                   | ❌ 拒絕（唯讀）             |
| `/tmp`                                   | ✅                          |
| image 內預先 `chown nonroot` 的目錄      | ✅                          |
| 具名 volume 掛到該目錄                   | ✅（繼承 image 內的擁有者） |
| bind mount 主機資料夾（擁有者 uid 1001） | ❌ 拒絕                     |

  所以要持久化寫入時，用**具名 volume，不要 bind mount 主機資料夾**。

- 驗證狀態：2026-10-24 已用 `docker compose up --build` 驗證含 RAG 的版本（`/health`、ui 回 200、`POST /chat` 經容器內 api 呼叫主機 Ollama 的 `bge-m3` 嵌入與 `qwen2.5:3b`、依節號取整節、容器內 `RAG_VERSION=B` 檢索，執行身分 uid 999）。索引在第一次請求時才建，不影響 `start_period`。之後若改了程式或依賴，繳交前須再驗證一次。

## 7. 已知問題與期末待辦

- **BM25 仍會被通用詞帶偏**：`teacher-012` 曾因此在版本 B 失敗，現在用「保證向量第 1 名進入 Top-K」補救（報告第 5 節，比較過 5 種做法）。但這只是讓 1-4-4 進入 Top-3（排第 3），BM25 本身的問題沒有解決；忽略高頻詞、調降 BM25 權重都試過，會換來別題失敗。
- **RRF 分數平手**：兩個排名互為鏡像時分數完全相同，次序由 `argsort` 決定（報告第 5 節）。可能的修法：平手時以向量相似度為第二排序鍵。
- **「N-N 節」規則只認這一種寫法**：「第三節」「1.3 節」不會觸發，會退回一般檢索。
- **3B 模型的限制**：摘要可能漏段落、偶爾補上教材沒有的推測句，prompt 要求的行內 `[id]` 引用也常被忽略。
- **只看最後一句**：檢索只用最後一輪訊息，追問（例如「那驗算呢？」）會找不到。
- **期末要做**：護欄（`out_of_scope`）、出題（`questions`）、Fact Critic、`llm.py` 與雲端路徑（`route`）。

## 8. 協作約定

- 各自用自己的帳號 commit（個人貢獻依 commit 紀錄評估）；目前開發分支 `dev/wang`。
- 規格有疑問以 `spec/` 與助教 repo 為準。
- **期中繳交流程**：(1) 文件與程式在 `dev/wang` 定稿（報告標頭、模板 `>` 說明都處理完）；(2) 開 PR 到 `main`，組員 checkout 該 PR 的 commit，跑 `docker compose up --build` 與 `tests/teacher.jsonl` 確認；(3) 合併時用 merge commit 或 rebase，**不要 squash**，否則驗證過的 commit 不在 `main` 的歷史裡；(4) 在 `main` 最新的 commit 上打 tag：`git tag midterm && git push origin refs/tags/midterm`；(5) 驗證通過後不再加 commit，真的要改就先通知組員，再刪除並重打 tag。
- **`midterm` 名稱衝突**：遠端目前已有一個 `midterm` **分支**（林祐任，commit `fce9294`，另一份 RAG 版本 A 實作）。分支與 tag 同名會讓 `git rev-parse midterm`、`git checkout midterm` 出現 ambiguous 警告；打 tag 前請和組員討論，把那個分支改名（例如 `dev/lin`）。該分支的 `api/app/rag.py`、`api/requirements.txt` 也與我們的 `api/app/rag/` 套件和 uv 依賴管理不相容，合併時 `pipeline.py` 會衝突，需要先處理。
