#!/usr/bin/make
lint:
	uv run pre-commit run --all-files

dev:
	uv run streamlit run panel/main.py --server.port 8501
