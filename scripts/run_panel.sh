#!/bin/bash
set -euo pipefail

echo "Starting the Poltergeist control room..."

exec uv run --no-sync streamlit run panel/main.py \
    --server.port "${PANEL_HTTP_PORT:=8501}" \
    --server.address 0.0.0.0 \
    --server.baseUrlPath "${PANEL_BASE_PATH:=/panel}" \
    --server.headless true
