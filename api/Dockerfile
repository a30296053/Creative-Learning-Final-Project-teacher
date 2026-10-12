# build context 是 repo 根目錄（見 docker-compose.yml），所以 COPY 路徑都從根目錄算起
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.0 /uv /bin/uv

WORKDIR /srv
# 使用映像內建的 Python，不要讓 uv 另外下載；啟動時不重新編譯 .pyc
ENV UV_PYTHON_DOWNLOADS=0 UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy \
    PATH="/srv/.venv/bin:$PATH"

# 先只裝依賴（pyproject.toml / uv.lock 沒變就能用快取），--locked：鎖檔過期就報錯
COPY pyproject.toml uv.lock .python-version ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --only-group api

COPY api/app ./app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
