# ClockRouter agent instructions

These instructions apply to the entire repository. A more local `AGENTS.md` may
add constraints for its subtree but may not weaken privacy or security rules.

## Mission

Build a local-first OpenAI-compatible gateway whose privacy and spending rules
are enforced in code. Prefer a small, inspectable system over cleverness.

## Source of truth

Read these in order before changing code:

1. `AGENTS.md`
2. `docs/CONSTITUTION.md`
3. the active `specs/NNN-name/spec.md`
4. its `plan.md` and `tasks.md`
5. relevant ADRs under `docs/adr/`
6. `docs/BEST_PRACTICES.md` when changing APIs, security, logging, CI, or containers
7. `docs/ECOSYSTEM_SURVEY.md` before adding routing/provider/telemetry dependencies

If these disagree, stop and surface the conflict. Do not silently reinterpret a
privacy or budget requirement.

## Required workflow

1. Identify one active spec. If none covers the request, draft one from
   `specs/_template/` before production code.
2. Make acceptance criteria observable and testable.
3. Write or update the implementation plan before editing production code.
4. Work only on tasks marked `[ ]`; mark a task `[x]` only after verification.
5. Keep changes focused. Record a new ADR for durable architectural choices.
6. Run `uv run ruff check .` and `uv run pytest` before claiming completion.
7. Update the spec's evidence table with commands and outcomes.

Tiny typo or comment-only changes may skip a new spec, but must still respect
the constitution and pass relevant checks.

## Non-negotiable safety rules

- Privacy is a hard eligibility constraint, never a weighted routing score.
- Unknown projects default to denial; never silently treat them as public.
- Local failure must not trigger cloud escalation unless project policy and the
  active spec explicitly allow it.
- Never log prompts, message bodies, credentials, authorization headers, or
  provider keys.
- Never commit `.env`, databases, request logs, secrets, or real API keys.
- Bind to localhost/private overlay networking by default.
- Cloud features require deterministic budget enforcement before dispatch.
- Tests must prove both allowed behavior and denied behavior.

## Engineering conventions

- Python 3.12+, typed code, async I/O at network boundaries.
- Keep provider behavior behind adapters; routing must not branch on provider
  names.
- Configuration is validated at startup and fails closed.
- Prefer explicit rules to an LLM classifier until measured evidence justifies
  a classifier.
- Preserve OpenAI-compatible response and streaming semantics.
- Add dependencies only when the standard library/current stack is inadequate;
  explain additions in `plan.md`.

## Completion report

At handoff, state: spec used, tasks completed, files changed, verification run,
known limitations, and the next uncompleted task. Never report a feature as
complete solely because code was written.
