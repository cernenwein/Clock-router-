.PHONY: install lint test test-parallel check

install:
	uv sync --dev

lint:
	uv run ruff check .

test:
	uv run pytest

test-parallel:
	uv run pytest -n auto

check: lint test-parallel
