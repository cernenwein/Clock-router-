# ClockRouter constitution

Version: 1.0.0  
Ratified: 2026-09-12

This document defines constraints that every feature specification and plan
must satisfy.

## I. Local first

Local inference is the default. Cloud processing is an explicit capability
granted per project, not a fallback assumption.

## II. Privacy is enforced

Privacy policy filters candidate routes before ranking or availability checks.
When no permitted route exists, ClockRouter fails closed with an actionable
error. Prompt content and secrets are never stored in routine telemetry.

## III. Spend is bounded

Any cloud dispatch must be checked against per-request, daily, and monthly
limits using a documented conservative estimate. Ambiguous accounting denies
or requires an explicit, auditable override.

## IV. Compatibility is tested

The gateway preserves the supported OpenAI API contract, including streaming.
Contract behavior is covered by tests rather than assumed from provider claims.

## V. Decisions are explainable

Each route produces a request ID, selected route, and non-sensitive reason.
Routing begins deterministic. Learned routing may be introduced only through a
spec that defines evaluation data, failure thresholds, rollback, and privacy
impact.

## VI. Changes are spec driven

Non-trivial production changes require an approved feature spec, implementation
plan, task list, acceptance tests, and verification evidence. Long-lived design
decisions receive an ADR.

## Amendment rule

Changing this constitution requires its own spec and an ADR. Amendments must
identify affected specs and migration work. A patch/minor/major version change
follows clarification/new principle/backward-incompatible principle semantics.
