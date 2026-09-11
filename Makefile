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

sync:
	rm -rf app && cp -r ../poltergeist/app app && rm -rf app/api app/main.py && sed -i '/from . import api/d' app/__init__.py
