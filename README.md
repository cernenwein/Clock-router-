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

## OpenCode

Configure an OpenAI-compatible provider with base URL
`http://littlemac:4000/v1`, then expose the virtual models `clock/local` and
`clock/auto`. Use the NetBird address rather than a public or general-LAN bind
when accessing LittleMac remotely.

## Development

```bash
uv run ruff check .
uv run pytest
```

License: MIT
