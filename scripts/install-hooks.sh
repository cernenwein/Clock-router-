#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required: https://docs.astral.sh/uv/getting-started/installation/" >&2
  exit 1
fi

uv sync --locked --dev
uv run pre-commit install --install-hooks
uv run pre-commit run --all-files
uv run pre-commit run --hook-stage pre-push --all-files

echo "ClockRouter pre-commit and pre-push hooks are installed and verified."
