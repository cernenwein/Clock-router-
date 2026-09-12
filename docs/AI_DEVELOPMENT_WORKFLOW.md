# AI development workflow

This workflow is designed so a new AI session can continue development without
access to previous chat history.

## 1. Orient

Read `AGENTS.md`, the constitution, roadmap, ADR index, and active spec. Inspect
the code and tests relevant to the next unchecked task. Do not infer completion
from filenames or prose.

## 2. Specify

Copy `specs/_template` to the next zero-padded feature number. Describe user
outcomes, boundaries, risks, acceptance scenarios, and out-of-scope behavior.
Resolve every `[NEEDS DECISION]` before implementation.

## 3. Plan

Document components, interfaces, configuration changes, migrations, threat
considerations, tests, and rollback. If the plan changes a durable architectural
decision, add an ADR.

## 4. Decompose

Create ordered tasks small enough to verify independently. Each task names its
files and validation. Mark parallel-safe tasks `[P]`; tasks without `[P]` are
assumed sequential.

## 5. Implement

Work one task at a time. Prefer tests that initially fail for the intended
reason. Keep task checkboxes and the change log current in the same commit as
the implementation.

## 6. Verify

Run the acceptance scenarios plus repository checks:

```bash
uv run ruff check .
uv run pytest
```

Record command, result, and date in `spec.md`. A failed or skipped required check
keeps the task open.

## 7. Review and hand off

Use `.github/pull_request_template.md`. Explain policy impact, evidence, known
limits, rollback, and next task. The next agent starts from repository state,
not undocumented conversation context.

## Status convention

- `Draft`: requirements may change; no production implementation.
- `Ready`: decisions resolved and plan reviewable.
- `Active`: implementation in progress.
- `Implemented`: acceptance evidence recorded.
- `Superseded`: replaced by a linked spec.
