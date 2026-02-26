.PHONY: run db fmt lint check test

run:
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

db:
	uv run python scripts/init_db.py

fmt:
	uv run black .

lint:
	uv run ruff check .

check: fmt lint

test:
	uv run pytest tests/ -v
