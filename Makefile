.PHONY: install test lint run-api run-worker demo clean \
       demo-infra demo-migrate demo-api demo-outbox demo-worker demo-ui demo-stop demo-all

install:
	pip install -e .
	pip install -r requirements.txt

test:
	pytest tests/unit

test-all:
	pytest tests/

lint:
	ruff check .
	mypy core adapters

run-api:
	uvicorn apps.api.main:app --reload --port 8000

run-worker:
	python -m worker.main

demo:
	python scripts/generate_dossiers.py
	pytest tests/smoke

clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type d -name "*.egg-info" -exec rm -r {} +

# ──────────────────────────────────────────────────
# Local Demo (Hybrid: Docker infra + native code)
# ──────────────────────────────────────────────────

demo-infra: ## Start only PostgreSQL + Redis in Docker
	docker compose -f infra/docker-compose.local.yml up -d

demo-migrate: ## Run Alembic migrations against local PG
	alembic upgrade head

demo-api: ## Start FastAPI server natively (auto-reload)
	uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload

demo-outbox: ## Start outbox dispatcher natively
	python -m apps.api.outbox_dispatcher

demo-worker: ## Start worker natively (ML inference on host)
	python -m worker.main

demo-ui: ## Start React Vite dev server (port 3000)
	cd apps/ui && npm run dev

demo-stop: ## Stop Docker infra containers
	docker compose -f infra/docker-compose.local.yml down

demo-all: ## One-shot: launch everything via PowerShell script
	powershell -ExecutionPolicy Bypass -File scripts/demo-local.ps1
