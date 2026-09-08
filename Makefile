.PHONY: install test lint run-api run-worker demo clean

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
