#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"
workers="\${CLOCKROUTER_TEST_WORKERS:-2}"

echo "Checking lockfile consistency..."
if ! uv lock --check; then
  echo "Push validation stopped: pyproject.toml and uv.lock disagree." >&2
  echo "Follow docs/VALIDATION_AND_VERSIONING.md; do not regenerate from a partial checkout." >&2
  exit 1
fi

echo "Running tests with \${workers} workers..."
uv run pytest -n "$workers"
echo "Local push validation passed. Remote branch CI will verify the same commit."
