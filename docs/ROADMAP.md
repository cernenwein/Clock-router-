# Roadmap

This file describes product direction. Approved implementation commitments live
in numbered `specs/` folders; roadmap bullets are not authorization to code.

## v0.1 — local foundation

- OpenAI-compatible chat-completions endpoint
- virtual models
- deterministic routing
- hard project privacy policy
- LM Studio-compatible proxying and streaming
- token authentication

## v0.2 — controlled cloud

- OpenRouter provider adapter
- SQLite usage accounting
- input/output token and cost capture
- per-request, daily, and monthly budget enforcement
- structured JSON request logs without prompt bodies

Tracking spec: create `specs/001-controlled-cloud/` before implementation.

## v0.3 — safe escalation

- explicit escalation chains
- retry only on defined transport, context, or structured-output failures
- project-specific escalation permission
- circuit breakers and provider health

## Later — evidence-based auto routing

- task heuristics informed by actual usage history
- model suitability and reliability scores
- `/v1/responses` compatibility
- admin status and spending endpoints
- opt-in evaluation feedback
