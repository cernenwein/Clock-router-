# Feature 001: Gateway hardening

- Status: Active
- Owner: Clockwork
- Created: 2026-09-12
- Updated: 2026-09-12

## Problem

The v0.1 gateway proves local routing but accepts an insecure default token,
trusts a caller-selected project, validates configuration late, accepts
unbounded request objects, and exposes unsafe upstream failure behavior. Cloud
routing must not be added until these boundaries fail closed.

## Outcomes

- Insecure credentials and invalid configuration prevent startup.
- An authenticated client can use only explicitly scoped projects.
- Supported requests are bounded and validated before routing or dispatch.
- Upstream failures return stable, sanitized OpenAI-shaped errors.
- The container runs as an unprivileged user with reduced privileges.
- Serial and parallel tests cover allowed and denied paths.

## Non-goals

- Cloud providers, pricing, accounting, budgets, fallback, retries,
  `/v1/responses`, multiple simultaneous client credentials, or learned routing.

## Requirements

- R1: `CLOCKROUTER_API_TOKEN` is required and rejects blank or known placeholder values.
- R2: `CLOCKROUTER_ALLOWED_PROJECTS` scopes the credential to configured projects.
- R3: Models, virtual models, and project policies use strict typed configuration.
- R4: Cross-references and cloud URLs validate at startup.
- R5: Chat requests require a supported virtual model and at least one valid message.
- R6: Request size and requested output-token limits are configurable and enforced.
- R7: Transport, timeout, upstream status, malformed JSON, and SSE failures are sanitized.
- R8: Error responses use a stable OpenAI-shaped envelope and request ID.
- R9: Upstream response bodies are never echoed on errors.
- R10: The container runs non-root, has a healthcheck, and drops privilege escalation.

## Acceptance scenarios

1. Missing or placeholder API credentials prevent application startup.
2. A valid token can use an allowed project but receives 403 for another known project.
3. Invalid model and policy references prevent configuration loading.
4. Malformed, empty, oversized, or over-limit requests are rejected before dispatch.
5. Timeout, connection, upstream error, and malformed JSON responses are sanitized.
6. SSE completes byte-for-byte normally and emits a sanitized SSE error on stream failure.
7. All checks pass serially and with parallel workers.

## Security, privacy, and cost

The client cannot self-authorize by changing a header. Raw upstream errors are
treated as sensitive. No cloud dispatch exists, so this feature incurs no model
cost. Ambient proxy variables remain disabled.

## Verification evidence

| Date | Command/scenario | Result |
|---|---|---|
| 2026-09-12 | `make validate` | 24 passed across 9 workers; Ruff passed |
| 2026-09-12 | `uv run pytest` | 24 passed serially |
| 2026-09-12 | `docker compose config` | Not run: Docker unavailable in development environment |

## Change log

- 2026-09-12: Spec activated from prioritized code review.
- 2026-09-12: Hardening implemented; container configuration awaits runtime verification.
