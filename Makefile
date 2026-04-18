.PHONY: up down logs ps build migrate rev shell fmt lint test

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f api

ps:
	docker compose ps

build:
	docker compose build

migrate:
	docker compose exec api alembic upgrade head

rev:
	docker compose exec api alembic revision --autogenerate -m "$(m)"

shell:
	docker compose exec api bash

fmt:
	ruff format app tests

lint:
	ruff check app tests
	mypy app

test:
	pytest -v
