# Feature 005: Typed provider adapters

- Status: Implemented
- Owner: Clockwork
- Created: 2026-09-13
- Updated: 2026-09-13

## Problem

The Chat Completions endpoint currently constructs provider URLs, rewrites model
names, sets upstream headers, and chooses HTTPX request modes directly. This
mixes routing and policy with transport behavior and makes future providers
tempting to add through unsafe provider-name branches.

## Outcomes

- Provider transport is isolated behind a small typed async protocol.
- Models select an adapter by protocol identifier, independently of provider branding.
- The existing OpenAI-compatible behavior is preserved for LM Studio and Ollama.
- Unknown adapter identifiers fail during startup before any request can dispatch.
- Tests can inject an adapter without changing routing or contacting a network.

## Non-goals

- Adding OpenRouter or another cloud service, provider-specific capability
  probing, retries, fallback, telemetry, `/v1/responses`, or changing routing
  strategy and budget decisions.

## Requirements

- R1: A typed `ProviderAdapter` protocol accepts a typed provider call and
  exposes separate async completion and streaming dispatch methods.
- R2: The OpenAI-compatible adapter owns endpoint construction, upstream model
  rewriting, request-ID propagation, JSON headers, and HTTPX dispatch mode.
- R3: `ModelConfig` selects an adapter with a backward-compatible
  `openai-compatible` default.
- R4: `Route` carries the configured adapter identifier without inspecting the
  provider name.
- R5: App startup rejects any configured adapter identifier that is not present
  in the adapter registry.
- R6: The application accepts an injected adapter registry for isolated tests;
  production defaults contain only the OpenAI-compatible adapter.
- R7: Existing authentication, privacy, routing, response validation, streaming,
  error normalization, and cloud-budget behavior remain unchanged.
- R8: Local provider failure never invokes a second adapter or cloud route.

## Acceptance scenarios

1. Given an OpenAI-compatible route, the adapter posts to `/chat/completions`,
   replaces the virtual model with the upstream model, and propagates a safe
   request ID.
2. Given a streaming request, the adapter uses streaming HTTP dispatch while the
   gateway retains ownership of validation and response cleanup.
3. Given differently branded providers using the same adapter identifier, both
   dispatch through the same injected adapter without provider-name branches.
4. Given an unavailable adapter identifier, application startup fails before
   dispatch.
5. Given a local transport failure, the gateway returns its existing sanitized
   error and does not try another adapter.

## Security, privacy, and cost

Adapters receive the request payload only after authentication, project policy,
routing eligibility, and cloud-budget checks. They do not log content or
credentials. The registry is local application state and performs no discovery
or network calls. This spec adds no provider or fallback, so it creates no new
cloud-data path or model spend.

## Verification evidence

| Date | Command/scenario | Result |
|---|---|---|
| 2026-09-13 | Focused adapter tests | Passed, 20 tests |
| 2026-09-13 | `make validate` | Ruff passed; 83 tests passed across 9 workers |
| 2026-09-13 | `uv run pytest -q` | Passed, 83 tests serially |

## Change log

- 2026-09-13: Spec activated; adapter extraction and fail-closed registry selected.
- 2026-09-13: Typed OpenAI-compatible dispatch and startup-validated registry implemented.
- 2026-09-13: Serial and parallel acceptance evidence passed; spec implemented.
