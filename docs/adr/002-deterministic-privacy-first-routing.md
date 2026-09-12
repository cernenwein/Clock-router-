# ADR-002: Use deterministic privacy-first routing

- Status: Accepted
- Date: 2026-09-12
- Spec: `specs/000-clockrouter-foundation/`

## Context

An AI classifier adds cost, latency, nondeterminism, and a new path through
which protected content might leave the host.

## Decision

Apply project privacy as a hard candidate filter, then select routes using
explicit deterministic rules. Unknown project policies fail closed.

## Consequences

Routing is predictable and testable. It may be less adaptive until usage data
supports a separately specified learned router.

## Alternatives considered

LLM classification and weighted privacy scoring were rejected for the initial
system. Privacy cannot be traded for quality, latency, or cost.
