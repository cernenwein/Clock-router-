# Feature 004: Provider contract hardening

- Status: Implemented
- Owner: Clockwork
- Created: 2026-09-13
- Updated: 2026-09-13

## Problem

ClockRouter normalizes several provider failures, but its supported upstream
contract is not yet explicit enough to detect wrong content types, malformed
success envelopes, truncated SSE streams, or resource leaks. Provider claims of
OpenAI compatibility are insufficient without fixtures and lifecycle tests.

## Outcomes

- LM Studio and Ollama response shapes have sanitized, offline contract fixtures.
- Invalid non-streaming and streaming responses fail with stable, safe errors.
- Tool-call responses pass through without ClockRouter interpreting arguments.
- Upstream streaming responses close after success, failure, or cancellation.
- CI exercises the contract without contacting a model or external service.

## Non-goals

- Provider-adapter extraction, retries, fallback, cloud integration, prompt
  logging, capability discovery, or the `/v1/responses` endpoint.

## Requirements

- R1: A successful non-streaming upstream response must use a JSON media type
  and contain a JSON object; otherwise ClockRouter returns
  `invalid_upstream_response` without disclosing upstream content.
- R2: Sanitized LM Studio and Ollama fixtures must cover ordinary assistant text,
  usage metadata, and tool calls.
- R3: ClockRouter must preserve supported response fields and opaque tool-call
  arguments when proxying a valid response.
- R4: A successful streaming upstream response must use
  `text/event-stream`; otherwise ClockRouter closes it and returns a sanitized
  `invalid_upstream_response` error before streaming begins.
- R5: A stream that ends without an OpenAI `[DONE]` event must append a sanitized
  `upstream_stream_incomplete` event and terminate cleanly.
- R6: Upstream streaming responses must close on normal completion, upstream
  failure, and downstream cancellation.
- R7: Upstream 4xx/5xx, timeout, connection, malformed-response, and stream
  errors must not expose provider bodies, exception text, prompts, or secrets.
- R8: Contract tests must pass serially and with `pytest-xdist` and perform no
  live network access.

## Acceptance scenarios

1. Given either provider fixture, a valid JSON completion is returned unchanged
   except for ClockRouter's routing headers.
2. Given a tool-call completion, its function name and argument string are
   preserved exactly as opaque data.
3. Given a 200 response with a non-JSON media type or non-object JSON body, the
   client receives a sanitized 502 error.
4. Given a 200 stream with a non-SSE media type, the response is closed and the
   client receives a sanitized 502 error.
5. Given a truncated SSE stream, the client receives a sanitized terminal error
   followed by `[DONE]` and the upstream response closes.
6. Given downstream cancellation, the cancellation propagates and the upstream
   response closes without cloud fallback.

## Security, privacy, and cost

Fixtures use synthetic content and contain no real endpoints, model prompts,
responses, credentials, or machine identifiers. Errors expose only stable
ClockRouter categories and request IDs. Tests are offline. This feature neither
adds cloud routes nor changes budget policy, so cloud spend remains impossible
for the covered local configuration.

## Verification evidence

| Date | Command/scenario | Result |
|---|---|---|
| 2026-09-13 | Focused provider-contract tests | Passed, 36 tests |
| 2026-09-13 | `make validate` | Ruff passed; 74 tests passed across 9 workers |
| 2026-09-13 | `uv run pytest -q` | Passed, 74 tests serially |

## Change log

- 2026-09-13: Spec activated with provider contracts and lifecycle behavior in scope.
- 2026-09-13: Contract fixtures, strict response validation, and stream cleanup implemented.
- 2026-09-13: Serial and parallel acceptance evidence passed; spec implemented.
