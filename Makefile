.PHONY: venv install fmt lint type test dev run docker-build up down pre-commit


venv:
	python -m venv .venv && . .venv/bin/activate || .venv\\Scripts\\activate


install:
	python -m pip install --upgrade pip
	pip install -e .
	pip install -e .[dev]


fmt:
	ruff format .


lint:
	ruff check --fix .


type:
	mypy src


test:
	pytest


dev:
	uvicorn app.main:app --reload --factory --host 0.0.0.0 --port 8000 --app-dir src


run:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir src


pre-commit:
	pre-commit install
	pre-commit run --all-files


docker-build:
	docker build -t fastapi-service:dev .


up:
	docker compose up -d --build


down:
	docker compose down
