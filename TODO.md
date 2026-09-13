# ClockRouter TODO

Last reviewed: 2026-09-13  
Current baseline: v0.2 hardening, 74 tests passing serially and in parallel

This is the cross-spec queue. Detailed requirements, design, and completion
evidence belong in numbered `specs/` folders. An item moves to `Done` only after
its spec acceptance evidence passes.

## P0 — harden before any cloud traffic

- [x] **T-001: Reject insecure API-token defaults at startup.**
  Create Spec 001. Production startup must reject an absent, blank, or
  `change-me` token. Tests must inject a dedicated test token rather than rely
  on the application default.

- [x] **T-002: Replace loose YAML dictionaries with validated configuration models.**
  Validate provider, model, URL, strategy, target, project policy, timeout, and
  default-project references at startup. Unknown fields and unsafe cloud model
  configuration must fail closed with useful errors.

- [x] **T-003: Bind project authorization to client credentials.**
  Possession of one gateway token must not let a caller claim any project name
  and thereby select a cloud-enabled policy. Define token-to-project scopes or
  an equally strong authorization mechanism before cloud routing exists.

- [x] **T-004: Normalize upstream failures without leaking content.**
  Catch connection, DNS, timeout, TLS, malformed JSON, invalid content-type,
  disconnect, and streaming failures. Return stable OpenAI-shaped errors with a
  request ID; do not echo raw upstream bodies that may contain prompt data.

- [x] **T-005: Enforce request limits and schemas.**
  Validate the supported Chat Completions subset, cap request-body size and
  declared output tokens, reject unsupported fields deliberately, and test
  malformed JSON and oversized requests.

- [x] **T-006: Add budget accounting before the first cloud adapter.**
  Implement conservative pre-dispatch estimates plus per-request, daily, and
  monthly enforcement. Unknown price or token estimates must deny cloud use.
  Spec 002 implements atomic reservations, typed prices, pre-dispatch denial,
  reconciliation, local bypass, and threaded contention tests.

## P1 — reliability and operational safety

- [x] **T-007: Expand failure-path and cancellation tests.**
  Cover upstream 4xx/5xx, timeouts, connection refusal, non-JSON responses,
  partial SSE, client cancellation, upstream cancellation, and guaranteed
  response closure. Run each serially and with `pytest-xdist`.

- [ ] **T-008: Introduce provider adapters.**
  Move transport-specific behavior out of `main.py` behind a typed provider
  protocol. Routing selects capabilities/models; it must not branch on provider
  names.

- [ ] **T-009: Add privacy-minimal structured observability.**
  Record request ID, client/project identifiers, route reason, timing, status,
  token counts, and cost. Never record prompts, completions, credentials, or raw
  error bodies. Add redaction tests.

- [ ] **T-010: Harden the container.**
  Run as a non-root user, add a healthcheck, use a read-only filesystem where
  practical, document writable paths, and test the Compose deployment locally.
  Pin GitHub Actions to reviewed commit SHAs.

- [x] **T-011: Add configuration and API contract fixtures.**
  Maintain valid/invalid configuration fixtures and sanitized OpenAI/LM Studio/
  Ollama response fixtures. Verify headers, status mapping, tool calls, usage,
  and SSE framing without requiring live providers in CI.

- [ ] **T-012: Add coverage and static typing gates.**
  Select a coverage floor after measuring the baseline, publish missing lines in
  CI, and add a strict-enough type checker without silencing unexplained errors.

## P2 — controlled functionality

- [ ] **T-013: Add the OpenRouter provider adapter.**
  Base contract cases on official OpenRouter examples. Keep credentials on the
  gateway and require project authorization plus budget checks before dispatch.

- [ ] **T-014: Add accounting migrations and operational lifecycle.**
  Version the existing SQLite schema; add forward migrations, retention and
  recovery policy, operational queries, and crash-safety tests.

- [ ] **T-015: Add explicit retry and fallback policies.**
  Distinguish retry from escalation; apply privacy and budget eligibility on
  every candidate and attempt. Bound total deadlines and retry counts.

- [ ] **T-016: Add `/v1/responses`.**
  Specify the supported contract, streaming events, state behavior, and
  deliberate omissions before implementation.

- [ ] **T-017: Add Ollama and configurable LM Studio adapters.**
  Probe observed capabilities rather than trusting labels and keep local
  endpoints on explicit allowlists. Spec 003 establishes the offline-safe
  operator harness and branch validation needed before adapter extraction.

## P3 — evidence-based routing

- [ ] **T-018: Build an opt-in, redacted evaluation corpus.**
- [ ] **T-019: Define success and escalation feedback signals.**
- [ ] **T-020: Benchmark deterministic routing against candidate classifiers.**
- [ ] **T-021: Add learned routing only if it beats thresholds with rollback.**

## Done

- [x] Local OpenAI-compatible Chat Completions proxy.
- [x] Virtual `clock/local` and deterministic `clock/auto` models.
- [x] Hard cloud denial for local-only projects.
- [x] Bearer-token check for `/v1` endpoints.
- [x] Non-streaming and SSE proxy paths.
- [x] Serial and parallel test framework with eight baseline tests.
- [x] Spec-driven workflow, constitution, ADRs, CI, and ecosystem survey.
- [x] Local pre-commit/pre-push validation and version-preservation guide.
- [x] OpenAI SDK coding-harness reference client for the `clock/local` boundary.
- [x] Sanitized provider contracts and streaming lifecycle enforcement.

## Current review focus

- Transport logic remains concentrated in the endpoint rather than provider adapters.
- Structured telemetry, a coverage threshold, and a static type-check gate remain pending.
- Provider transport still needs extraction behind typed adapters in Spec 005.
- SQLite accounting exists, but schema migrations and lifecycle policy are not yet defined.
- Spec 003 is active for branch-first validation and local-provider harness preparation.
