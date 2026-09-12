# Implementation plan: ClockRouter foundation

## Constitution check

- Local-first: `clock/auto` selects a local model in v0.1.
- Privacy: project eligibility is checked before returning a route.
- Budget: no cloud dispatch exists yet.
- Compatibility: Chat Completions JSON and SSE bytes are proxied.
- Explainability: route and request IDs are response headers.

## Design

A FastAPI modular monolith loads YAML configuration at startup. The routing
module resolves virtual models without network access. The API layer authenticates,
selects a route, substitutes the upstream model name, and proxies via `httpx`.

## Test strategy

Unit tests cover deterministic local selection and hard private-project denial.
API contract and streaming integration coverage are deferred to the first
hardening spec.

## Risks and rollback

Provider dialect differences may violate compatibility. Keep the service local,
pin dependencies, and revert the application commit if client behavior regresses.
