# ADR-001: Begin as a modular monolith

- Status: Accepted
- Date: 2026-09-12
- Spec: `specs/000-clockrouter-foundation/`

## Context

ClockRouter needs policy, routing, provider, and accounting boundaries but does
not need distributed deployment complexity.

## Decision

Use one Python/FastAPI application with explicit internal modules and SQLite
when persistence is introduced. Deploy it as one container.

## Consequences

Development, testing, and deployment stay simple. Module interfaces preserve a
future extraction path if measured scale requires it.

## Alternatives considered

Microservices and Kubernetes were rejected because they add failure modes and
operational work without solving a present requirement.
