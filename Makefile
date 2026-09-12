.PHONY: install install-hooks format-check lint test test-parallel validate check

install:
	uv sync --dev

install-hooks:
	bash scripts/install-hooks.sh

format-check:
	uv run ruff format --check .

lint:
	uv run ruff check .

test:
	uv run pytest

test-parallel:
	uv run pytest -n auto

validate: format-check lint test-parallel

check: validate
