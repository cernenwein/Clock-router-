# Implementation plan: Gateway hardening

## Constitution check

- Local-first: no cloud adapter is introduced.
- Privacy: credential scope precedes route selection and raw failures are suppressed.
- Budget: cloud remains unavailable; limits cap local request exposure.
- Compatibility: successful Chat Completions and SSE pass through unchanged.
- Explainability: sanitized errors and successful responses carry request IDs.

## Design

Pydantic settings validate runtime security. Strict configuration models replace
nested dictionaries and perform cross-reference validation. Authentication
returns a client identity carrying allowed projects. The API parses bounded raw
bodies into a permissive-but-bounded Chat Completions schema, preserving unknown
provider fields while validating the routing-critical subset.

Transport helpers map upstream failures to stable errors. Normal streaming stays
byte-transparent; mid-stream failures emit one sanitized SSE error event and
`[DONE]`, then close the upstream response.

## Files and interfaces

| Path/interface | Change |
|---|---|
| `clockrouter/config.py` | Strict settings and YAML models |
| `clockrouter/schemas.py` | Request and error contracts |
| `clockrouter/main.py` | App factory, scoped auth, limits, error mapping |
| `clockrouter/routing.py` | Consume typed configuration |
| `tests/` | Configuration, auth, limit, failure, and stream tests |
| `Dockerfile`, Compose | Non-root runtime and health controls |

## Configuration and migration

Operators must set a non-placeholder `CLOCKROUTER_API_TOKEN`. The new
`CLOCKROUTER_ALLOWED_PROJECTS` value is comma-separated and defaults only to
`private`. Request bytes default to 1 MiB and `max_tokens` to 32,768.

## Test strategy

Pure unit tests cover settings/config/routing. ASGI tests mock upstream transport
for success, errors, malformed responses, and streams. The suite runs serially
and with isolated `pytest-xdist` workers.

## Risks and rollback

Strict startup can reject previously tolerated configurations; errors name the
invalid field without exposing secrets. Roll back the feature commit to restore
v0.1, but do not add cloud routing while rolled back.
