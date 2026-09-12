# Router and utility ecosystem survey

Reviewed: 2026-09-12

## Executive recommendation

Keep ClockRouter's policy core small and owned locally. Do not fork or embed a
full gateway yet. Use the official OpenRouter examples as protocol fixtures,
study LiteLLM and Portkey for failure-handling patterns, and reserve learned or
semantic routing for a later evidence-backed spec.

OpenRouter publishes SDKs, examples, tools, and documentation, but its hosted
routing backend is not the open-source repository we are building from.
Consequently, the useful comparison set is open-source gateways and routing
libraries—not forks of an official OpenRouter server.

Popularity is a discovery signal, not a quality or safety guarantee. Counts and
last-push dates below are a point-in-time GitHub snapshot and will drift.

## Shortlist

| Project | Snapshot | License signal | Best use for ClockRouter | Decision |
|---|---:|---|---|---|
| [LiteLLM](https://github.com/BerriAI/litellm) | 58.6k stars; pushed 2026-09-12 | GitHub reports `NOASSERTION`; inspect current terms before copying | Provider normalization, retries, fallback, cost tables | Study patterns; no dependency yet |
| [Portkey Gateway](https://github.com/Portkey-AI/gateway) | 13.0k stars; pushed 2026-05-25 | MIT | Config-driven gateway, guardrail and fallback concepts | Design reference; TypeScript does not fit v0.x core |
| [RouteLLM](https://github.com/lm-sys/RouteLLM) | 5.5k stars; last push 2024-08-10 | Apache-2.0 | Router evaluation methods and cost/quality tradeoffs | Research reference; not runtime code |
| [Semantic Router](https://github.com/aurelio-labs/semantic-router) | 3.9k stars; pushed 2026-09-12 | MIT | Fast semantic classification and route layers | Revisit only after deterministic baseline data |
| [Helicone](https://github.com/Helicone/helicone) | 6.2k stars; pushed 2026-09-11 | Apache-2.0 | Observability and evaluation concepts | Optional integration later; prompt capture off by default |
| [Langfuse](https://github.com/langfuse/langfuse) | 34.5k stars; pushed 2026-09-12 | GitHub reports `NOASSERTION`; verify licensing | Tracing/evaluation UI concepts | Do not integrate until data and license review |
| [TensorZero](https://github.com/tensorzero/tensorzero) | 11.7k stars; archived | Apache-2.0 | Gateway/evaluation architecture lessons | Reference only; exclude as dependency while archived |

## Official OpenRouter utilities

| Repository | Useful material | ClockRouter action |
|---|---|---|
| [OpenRouter Python SDK](https://github.com/OpenRouterTeam/python-sdk) | Current request types and OpenRouter-specific options | Evaluate for control-plane calls; retain raw `httpx` for transparent SSE proxying unless a spec proves benefit |
| [OpenRouter examples](https://github.com/OpenRouterTeam/openrouter-examples) | Cross-language API behavior and feature examples | Convert relevant examples into sanitized contract fixtures |
| [Python examples](https://github.com/OpenRouterTeam/openrouter-examples-python) | Minimal Python calls | Use to verify headers, errors, streaming, and usage fields during Spec 001 |
| [Tool support check](https://github.com/OpenRouterTeam/openrouter-tool-check) | Model tool-calling probes | Borrow the capability-test idea; do not trust static capability labels alone |
| [Benchmark harness](https://github.com/OpenRouterTeam/benchmark-harness) | Reproducible evaluation structure | Borrow dataset/result provenance concepts for later route evaluation |

The official Python SDK and benchmark harness are Apache-2.0 at this review.
Examples should still be checked file-by-file before copying because repository
and file licensing can change.

## What to borrow first

### 1. Provider capability discovery

Store declared capabilities separately from observed capability checks. A model
may advertise tool or structured-output support yet fail a concrete probe. Cache
probe results with timestamps and never allow capability checks to weaken
project privacy.

### 2. Retry, fallback, and circuit-breaker semantics

Separate retrying the same permitted provider from escalating to a different
model. Retries need bounded attempts, jitter, total deadlines, retryable-status
rules, and cancellation propagation. Fallback candidates must pass privacy and
budget gates again.

### 3. Cost metadata with provenance

Price records need provider, model, effective date, source, input/output units,
and conservative handling for unknown prices. Remote price refresh belongs in a
control-plane job; request dispatch must not depend on a live catalog fetch.

### 4. Evaluation before intelligent routing

Use RouteLLM and official benchmark-harness ideas to build a local evaluation
corpus from redacted, opt-in examples. Compare a deterministic baseline against
new routing logic on quality, privacy violations, cost, latency, and abstention.
No learned router ships without rollback thresholds.

### 5. Privacy-minimal observability

Borrow trace structure, not default prompt collection. ClockRouter telemetry
should contain IDs, route reasons, timing, token counts, costs, statuses, and
sanitized error categories. Content capture is a separate opt-in feature with
retention and access rules.

## What not to adopt yet

- A full gateway dependency whose policy behavior ClockRouter cannot easily audit.
- A fork that requires continuously merging a large upstream codebase.
- An LLM/embedding classifier before baseline success data exists.
- Automatic fallback that treats provider failure as cloud authorization.
- Observability stacks that require storing prompts or completions.
- A repository whose license is unclear, incompatible, or changed without review.
- Archived infrastructure as a production dependency.

## Evaluation checklist for a new candidate

1. Record canonical repository, commit/tag, license, last release, and activity.
2. Map the exact needed capability; reject vague “platform” adoption.
3. Inspect transitive dependencies, network calls, telemetry, and secret handling.
4. Prototype behind a ClockRouter-owned interface.
5. Add contract, denied-path, cancellation, timeout, and malformed-response tests.
6. Measure local memory, latency, startup, and operational cost.
7. Document removal/rollback before merging.
8. Create an ADR if adoption changes an architectural boundary.

## Near-term consequences

- Spec 001 should implement OpenRouter with a small provider adapter and contract
  fixtures based on official examples, not by importing an entire gateway.
- Spec 002 should add accounting and conservative price provenance before cloud
  auto-routing.
- Learned routing remains a later experiment after sufficient redacted evaluation
  data exists.
