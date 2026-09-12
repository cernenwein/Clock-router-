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
  -H "Authorization: Bearer $CLOCKROUTER_API_TOKEN" \
  -H 'Content-Type: application/json' \
  -H 'X-ClockRouter-Project: private' \
  -d '{"model":"clock/auto","messages":[{"role":"user","content":"Hello"}]}'
```

Generate a gateway token rather than using an example value:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

`CLOCKROUTER_ALLOWED_PROJECTS` is a comma-separated credential scope. The
default is `private`; listing a project in `policies.yaml` does not authorize a
credential to use it.

## Current safety behavior

- The service binds to localhost by default.
- Every `/v1` request requires the ClockRouter API token.
- Projects marked `cloud_allowed: false` can only use local models.
- `clock/auto` is deterministic in v0.1; no classifier sends requests elsewhere.
- Provider keys remain on the ClockRouter host.
- Local requests do not reserve or consume cloud budget.
- Cloud requests reserve conservative estimated cost atomically before dispatch.

## Local models

`clock/local` targets the `local-coder` entry in `config/models.yaml`; the
default URL is LM Studio on `host.docker.internal:1234`. When ClockRouter runs
outside Docker, change that URL to the local model server address, commonly
`http://127.0.0.1:1234/v1`. Local models require no pricing block, stay eligible
for `cloud_allowed: false` projects, and write no charge to the budget ledger.

`clock/auto` also selects a local model in the current deterministic router.
Cloud fallback is not automatic.

## Cloud budget controls

Cloud models must declare exact input and output prices per million tokens.
Global limits live in `config/budgets.yaml`, and SQLite state lives at
`CLOCKROUTER_DATABASE_PATH` (default `data/clockrouter.db`). ClockRouter reserves
the conservative estimate before making a cloud request and replaces it with
actual cost only when a non-streaming provider response includes trustworthy
token usage. Streaming and failed requests retain their conservative reservation.

See [`docs/ROADMAP.md`](docs/ROADMAP.md) for planned providers and escalation.

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

Install automatic commit and push validation once per clone:

```bash
bash scripts/install-hooks.sh
```

See [`docs/VALIDATION_AND_VERSIONING.md`](docs/VALIDATION_AND_VERSIONING.md) for
the hook behavior, GitHub CI boundary, feature-branch workflow, version tags,
recovery, and cost model.

License: MIT
