# ADR-003: Select provider adapters by protocol

- Status: Accepted
- Date: 2026-09-13
- Spec: `specs/005-provider-adapters/`

## Context

ClockRouter supports branded providers that expose compatible HTTP contracts.
Branching transport logic on names such as LM Studio or Ollama would duplicate
behavior, couple routing to vendors, and make privacy and budget review harder.

## Decision

Each physical model selects a transport adapter by protocol identifier. Routing
carries that identifier without interpreting the provider brand. A local,
startup-validated registry resolves the identifier to a typed async adapter.
Adapters construct and dispatch upstream requests only; authentication, route
eligibility, budgets, error normalization, accounting, and fallback remain in
ClockRouter's policy layer.

## Consequences

Compatible providers share one audited implementation, tests can inject narrow
fakes, and new protocols have an explicit integration point. Configuration gains
one optional field, and startup must validate registry completeness. Adding a
new adapter does not itself make any project eligible to use it.

## Alternatives considered

Provider-name conditionals were rejected because branding does not define a
transport contract. A full external gateway dependency was rejected because it
would enlarge the trusted policy surface. Runtime plugin discovery was rejected
because it creates unnecessary code-loading and supply-chain risk.
