# Implementation plan: Provider contract hardening

## Constitution check

- Local-first behavior: all fixtures and tests are offline; no route or fallback changes.
- Privacy enforcement: response validation and errors never include upstream content.
- Budget enforcement: local requests remain outside the cloud ledger; no cloud feature is added.
- API compatibility: valid JSON and SSE responses, including tool calls, remain transparent.
- Explainability: existing request-ID and route headers remain intact on valid responses.

## Design

Keep dispatch in the current modular-monolith endpoint for this spec. Add small
media-type predicates and a streaming generator that forwards upstream bytes,
recognizes the terminal `[DONE]` event across arbitrary chunk boundaries, emits
one sanitized error event for incomplete or failed streams, and always closes
the upstream response in `finally`.

Validate successful non-streaming responses before forwarding: require a JSON
media type, successful JSON decoding, and an object top-level envelope. Treat
tool-call contents and arguments as opaque JSON and pass them through unchanged.

Provider-specific behavior remains represented only by sanitized contract
fixtures. A typed adapter boundary is intentionally deferred to Spec 005.

## Files and interfaces

| Path/interface | Change |
|---|---|
| `specs/004-provider-contract-hardening/` | Scope, plan, tasks, and evidence |
| `clockrouter/main.py` | Validate upstream media types/envelopes and own stream cleanup |
| `tests/fixtures/providers/` | Sanitized LM Studio, Ollama, tool-call, and SSE fixtures |
| `tests/test_provider_contract.py` | Offline provider contract and passthrough tests |
| `tests/test_stream_lifecycle.py` | Completion, failure, truncation, and cancellation closure tests |
| `tests/test_api.py` | Gateway-level denied and malformed-response assertions |
| `TODO.md` | Current baseline and completed cross-spec contract-fixture item |

## Configuration and migration

No configuration, dependency, database, or API migration is required. Valid
OpenAI-compatible JSON and SSE responses continue to pass through. A provider
that labels JSON as a non-JSON media type or SSE as another media type will now
fail closed with a stable 502 response.

## Test strategy

- Load every provider fixture from disk and assert it is synthetic and valid.
- Parameterize valid completion passthrough for LM Studio and Ollama shapes.
- Verify opaque tool-call preservation and usage-field preservation.
- Reject wrong content types and non-object success envelopes.
- Exercise SSE framing split across chunks and missing `[DONE]` termination.
- Directly cancel the proxy generator and assert cancellation propagation and closure.
- Re-run existing upstream 4xx/5xx, timeout, connection, malformed JSON, and
  mid-stream error redaction tests.
- Run Ruff, parallel pytest, and serial pytest.

## Risks and rollback

Strict media-type checks may expose incorrectly configured providers that were
previously accepted accidentally. Operators can fix the provider's compatibility
configuration; rollback is a focused revert of the validation helpers and tests.
SSE terminal detection buffers only enough trailing bytes to recognize event
boundaries and does not parse or store model content.
