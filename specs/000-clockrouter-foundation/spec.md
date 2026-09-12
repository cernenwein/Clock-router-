# Feature 000: ClockRouter foundation

- Status: Implemented
- Owner: Clockwork
- Created: 2026-09-12
- Updated: 2026-09-12

## Problem

AI clients need one stable endpoint for local inference while project privacy
rules remain enforceable independently of client behavior.

## Outcomes

- OpenAI-compatible clients can list virtual models and request chat completions.
- Requests are forwarded to an OpenAI-compatible local provider.
- Private projects cannot select a cloud route.
- Streaming responses pass through without buffering the complete response.

## Non-goals

- Cloud provider dispatch, accounting, budget enforcement, automatic
  escalation, learned classification, and `/v1/responses`.

## Requirements

- R1: Expose `/health`, `/v1/models`, and `/v1/chat/completions`.
- R2: Require bearer authentication for `/v1` endpoints.
- R3: Resolve `clock/local` and deterministic `clock/auto` virtual models.
- R4: Apply project cloud eligibility before selecting a route.
- R5: Proxy streaming and non-streaming local responses.
- R6: Default deployment exposure to localhost.

## Acceptance scenarios

1. Given a configured local model, `clock/auto` selects it.
2. Given a private project and cloud target, routing raises a denial.
3. Given a valid token, the virtual model list is available.
4. Given an invalid token, the API returns 401.

## Security, privacy, and cost

Provider credentials stay on the gateway. Default project policy is private.
Prompt bodies are not logged. This feature dispatches no paid cloud requests.

## Verification evidence

| Date | Command/scenario | Result |
|---|---|---|
| 2026-09-12 | `uv run ruff check .` | Passed |
| 2026-09-12 | `uv run pytest` | 2 passed |

## Change log

- 2026-09-12: Foundation implemented and workflow documentation added.
