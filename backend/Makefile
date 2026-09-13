.PHONY: help install run worker beat migrate migration test lint format up down logs shell

help:
	@echo "make install    - install python dependencies"
	@echo "make run        - run the API with reload (dev)"
	@echo "make worker     - run a celery worker"
	@echo "make beat       - run celery beat (scheduled jobs)"
	@echo "make migrate    - apply alembic migrations"
	@echo "make migration  - autogenerate a new alembic migration (m=\"message\")"
	@echo "make test       - run the test suite with coverage"
	@echo "make lint       - run ruff + mypy"
	@echo "make format     - auto-format with ruff"
	@echo "make up         - docker compose up (full stack)"
	@echo "make down       - docker compose down"
	@echo "make logs       - tail docker compose logs"
	@echo "make shell      - open a shell in the running api container"

install:
	pip install -r requirements.txt

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

worker:
	celery -A app.workers.celery_app worker --loglevel=info

beat:
	celery -A app.workers.celery_app beat --loglevel=info

migrate:
	alembic upgrade head

migration:
	alembic revision --autogenerate -m "$(m)"

test:
	pytest --cov=app --cov-report=term-missing

lint:
	ruff check app tests
	mypy app

format:
	ruff check --fix app tests
	ruff format app tests

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

shell:
	docker compose exec api /bin/bash
