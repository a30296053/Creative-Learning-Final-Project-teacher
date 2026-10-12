# build context 是 repo 根目錄（見 docker-compose.yml），所以 COPY 路徑都從根目錄算起
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.0 /uv /bin/uv

WORKDIR /srv
ENV UV_PYTHON_DOWNLOADS=0 UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy \
    PATH="/srv/.venv/bin:$PATH"

COPY pyproject.toml uv.lock .python-version ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --only-group ui

COPY ui/app.py .
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
