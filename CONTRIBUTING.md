# Contributing

ClockRouter uses spec-driven development. Read `AGENTS.md` and
`docs/CONSTITUTION.md` first.

For a behavior change, create or update a numbered spec, resolve its decisions,
write the plan, and decompose tasks before production code. Pull requests must
link the spec, update its checkboxes and evidence, and use the repository PR
template.

Before opening a pull request:

```bash
uv sync --dev
uv run ruff check .
uv run pytest
uv run pytest -n auto
```

Run `bash scripts/install-hooks.sh` once per clone to enforce formatting, lint,
lockfile integrity, whitespace, and parallel tests automatically. Full behavior
and bypass policy are documented in `docs/VALIDATION_AND_VERSIONING.md`.

Never include credentials, prompt data, real request logs, `.env`, or databases
in issues, specs, commits, or test fixtures.
