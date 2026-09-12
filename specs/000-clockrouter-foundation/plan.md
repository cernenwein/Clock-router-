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
FastAPI contract tests cover health, authentication, virtual model discovery,
unknown-project denial, upstream model rewriting, route metadata, and SSE byte
forwarding. `pytest-xdist` verifies that the suite can run in isolated parallel
worker processes without shared event-loop or application-state collisions.

## Risks and rollback

Provider dialect differences may violate compatibility. Keep the service local,
pin dependencies, and revert the application commit if client behavior regresses.
