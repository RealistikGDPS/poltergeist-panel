#!/usr/bin/make
build:
	docker compose build

run:
	docker compose up -d

stop:
	docker compose down

logs:
	docker compose logs -f panel

lint:
	uv run pre-commit run --all-files

dev:
	uv run streamlit run panel/main.py --server.port 8501

