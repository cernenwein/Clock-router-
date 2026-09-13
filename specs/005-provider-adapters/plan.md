# Implementation plan: Typed provider adapters

## Constitution check

- Local-first behavior: the default adapter preserves existing local routing.
- Privacy enforcement: adapter selection happens only after project eligibility.
- Budget enforcement: cloud reservation remains before adapter dispatch.
- API compatibility: OpenAI-compatible request, response, and SSE behavior is preserved.
- Explainability: existing request-ID, route, and latency headers remain unchanged.

## Design

Add `clockrouter/providers.py` with an immutable `ProviderCall`, a structural
`ProviderAdapter` protocol, an `OpenAICompatibleAdapter`, and a function that
constructs the production registry. The call contains the already-authorized
base URL, upstream model, sanitized request ID, and validated request payload.

The adapter owns only upstream request construction and dispatch. The FastAPI
application continues to own authentication, policy, budgets, error mapping,
response validation, accounting, and downstream response lifecycle. This keeps
provider code incapable of selecting routes or authorizing cloud use.

Add an `adapter` field to each physical model with a backward-compatible
`openai-compatible` default. Routing copies that identifier into `Route` without
branching on `provider`. App startup checks all configured identifiers against
the registry and fails closed if one is absent. `create_app` accepts an optional
registry for contract tests and future composition.

Record this stable boundary in ADR-003. No external dependency is needed.

## Files and interfaces

| Path/interface | Change |
|---|---|
| `specs/005-provider-adapters/` | Scope, design, tasks, and evidence |
| `docs/adr/003-provider-adapters-by-protocol.md` | Durable adapter-selection decision |
| `clockrouter/providers.py` | Typed call, protocol, default adapter, and registry |
| `clockrouter/config.py` | Backward-compatible model adapter identifier |
| `clockrouter/routing.py` | Carry adapter identifier in the selected route |
| `clockrouter/main.py` | Resolve adapter after policy/budget checks and dispatch through it |
| `config/models.yaml` | Explicit OpenAI-compatible adapter for the sample local model |
| `tests/test_providers.py` | Adapter request-construction unit tests |
| `tests/test_adapter_integration.py` | Registry injection, startup denial, and no-fallback tests |
| `tests/test_config.py` / `tests/test_routing.py` | Defaulting and route propagation tests |
| `TODO.md` | Baseline and provider-adapter task status |

## Configuration and migration

Existing model configuration remains valid because `adapter` defaults to
`openai-compatible`. The repository example will declare it explicitly. Unknown
or unavailable identifiers fail at application startup. Rollback removes the
field and restores direct HTTPX calls; no stored data migration is involved.

## Test strategy

- Unit-test normal and streaming dispatch with HTTPX mock transports.
- Assert endpoint, physical model rewrite, request ID, content type, and payload.
- Verify model configuration defaults and route propagation.
- Inject one recording adapter for multiple provider brand strings and prove the
  same adapter is used.
- Reject an unavailable adapter during lifespan startup.
- Inject a failing local adapter and prove exactly one dispatch with no fallback.
- Run all prior contract, budget, streaming, serial, and parallel tests unchanged.

## Risks and rollback

Application state gains one registry mapping, and call construction moves across
a module boundary. Tests compare the exact upstream request and retain all prior
failure coverage. The adapter protocol deliberately excludes routing, budgets,
logging, and fallback so later provider implementations cannot silently absorb
those responsibilities.
