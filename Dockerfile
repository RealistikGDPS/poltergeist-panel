FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /bin/uv

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY scripts /app/scripts
COPY logging.yaml /app/logging.yaml
COPY .streamlit /app/.streamlit
COPY app /app/app
COPY panel /app/panel

ENTRYPOINT ["/app/scripts/run_panel.sh"]
