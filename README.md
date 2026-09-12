# ClockRouter

ClockRouter is a local-first, OpenAI-compatible gateway for routing AI requests
between local and cloud models under explicit privacy and budget policies.

The v0.1 scaffold proxies `/v1/chat/completions` to an OpenAI-compatible local
server such as LM Studio. It exposes virtual model names (`clock/local` and
`clock/auto`) so clients do not need to know which physical model is running.

## Quick start

1. Copy `.env.example` to `.env` and adjust the settings.
2. Start an OpenAI-compatible model server at the configured URL.
3. Run ClockRouter:

```bash
uv sync --dev
uv run uvicorn clockrouter.main:app --host 127.0.0.1 --port 4000
```

Test it:

```bash
curl http://127.0.0.1:4000/health
curl http://127.0.0.1:4000/v1/chat/completions \
  -H 'Authorization: Bearer change-me' \
  -H 'Content-Type: application/json' \
  -H 'X-ClockRouter-Project: private' \
  -d '{"model":"clock/auto","messages":[{"role":"user","content":"Hello"}]}'
```

## Current safety behavior

- The service binds to localhost by default.
- Every `/v1` request requires the ClockRouter API token.
- Projects marked `cloud_allowed: false` can only use local models.
- `clock/auto` is deterministic in v0.1; no classifier sends requests elsewhere.
- Provider keys remain on the ClockRouter host.

See [`docs/ROADMAP.md`](docs/ROADMAP.md) for planned cloud routing, accounting,
budgets, and escalation.

## Spec-driven development

Every non-trivial change begins as a numbered folder under `specs/`. The folder
contains the problem and acceptance criteria (`spec.md`), technical approach
(`plan.md`), and executable work list (`tasks.md`). Agents must read
[`AGENTS.md`](AGENTS.md) before modifying the repository.

Start a feature from the template:

```bash
bash scripts/new-spec.sh "openrouter-provider"
```

Then work through the gates described in
[`docs/AI_DEVELOPMENT_WORKFLOW.md`](docs/AI_DEVELOPMENT_WORKFLOW.md). The current
system is captured in [`specs/000-clockrouter-foundation`](specs/000-clockrouter-foundation/).
See [`docs/BEST_PRACTICES.md`](docs/BEST_PRACTICES.md) for the primary sources
behind the workflow and the rules ClockRouter adopts from each.
See [`docs/ECOSYSTEM_SURVEY.md`](docs/ECOSYSTEM_SURVEY.md) before adding a router,
provider, observability, or evaluation dependency.
The prioritized engineering queue is maintained in [`TODO.md`](TODO.md).

## OpenCode

Configure an OpenAI-compatible provider with base URL
`http://littlemac:4000/v1`, then expose the virtual models `clock/local` and
`clock/auto`. Use the NetBird address rather than a public or general-LAN bind
when accessing LittleMac remotely.

## Development

```bash
uv run ruff check .
uv run pytest
uv run pytest -n auto  # parallel worker processes
```

The same commands are available as `make lint`, `make test`, and
`make test-parallel`. Parallel workers run in isolated processes so global ASGI
lifespans and event loops are not shared between tests.

License: MIT
