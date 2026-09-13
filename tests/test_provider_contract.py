import json
from pathlib import Path

import httpx
import pytest
import respx

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "providers"
UPSTREAM_URL = "http://host.docker.internal:1234/v1/chat/completions"


def load_fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURE_DIR / name).read_text())


@pytest.mark.parametrize(
    "fixture_name",
    ["lmstudio_completion.json", "ollama_completion.json"],
)
@respx.mock
async def test_provider_completion_fixture_passes_through(
    client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    fixture_name: str,
) -> None:
    payload = load_fixture(fixture_name)
    respx.post(UPSTREAM_URL).mock(return_value=httpx.Response(200, json=payload))

    response = await client.post(
        "/v1/chat/completions",
        headers=auth_headers,
        json={"model": "clock/local", "messages": [{"role": "user", "content": "test"}]},
    )

    assert response.status_code == 200
    assert response.json() == payload
    assert response.headers["x-clockrouter-route"] == "local-coder"


@respx.mock
async def test_tool_call_arguments_pass_through_as_opaque_data(
    client: httpx.AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    payload = load_fixture("tool_call_completion.json")
    respx.post(UPSTREAM_URL).mock(return_value=httpx.Response(200, json=payload))

    response = await client.post(
        "/v1/chat/completions",
        headers=auth_headers,
        json={"model": "clock/local", "messages": [{"role": "user", "content": "test"}]},
    )

    function = response.json()["choices"][0]["message"]["tool_calls"][0]["function"]
    assert function == {"name": "synthetic_lookup", "arguments": '{"value":42}'}


@pytest.mark.parametrize("media_type", ["application/json", "application/vnd.api+json"])
@respx.mock
async def test_json_media_types_are_accepted(
    client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    media_type: str,
) -> None:
    payload = load_fixture("lmstudio_completion.json")
    respx.post(UPSTREAM_URL).mock(
        return_value=httpx.Response(
            200,
            content=json.dumps(payload),
            headers={"content-type": f"{media_type}; charset=utf-8"},
        )
    )

    response = await client.post(
        "/v1/chat/completions",
        headers=auth_headers,
        json={"model": "clock/local", "messages": [{"role": "user", "content": "test"}]},
    )

    assert response.status_code == 200
    assert response.json() == payload


@respx.mock
async def test_non_json_success_media_type_is_rejected_without_body_disclosure(
    client: httpx.AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    respx.post(UPSTREAM_URL).mock(
        return_value=httpx.Response(
            200,
            text='{"secret":"synthetic-sensitive-body"}',
            headers={"content-type": "text/plain"},
        )
    )

    response = await client.post(
        "/v1/chat/completions",
        headers=auth_headers,
        json={"model": "clock/local", "messages": [{"role": "user", "content": "test"}]},
    )

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "invalid_upstream_response"
    assert "synthetic-sensitive-body" not in response.text


@respx.mock
async def test_non_object_json_success_is_rejected(
    client: httpx.AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    respx.post(UPSTREAM_URL).mock(return_value=httpx.Response(200, json=["not", "an", "object"]))

    response = await client.post(
        "/v1/chat/completions",
        headers=auth_headers,
        json={"model": "clock/local", "messages": [{"role": "user", "content": "test"}]},
    )

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "invalid_upstream_response"


@pytest.mark.parametrize("status_code", [400, 429, 500, 503])
@respx.mock
async def test_upstream_error_statuses_are_normalized_without_body_disclosure(
    client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    status_code: int,
) -> None:
    respx.post(UPSTREAM_URL).mock(
        return_value=httpx.Response(status_code, text="synthetic-sensitive-error-body")
    )

    response = await client.post(
        "/v1/chat/completions",
        headers=auth_headers,
        json={"model": "clock/local", "messages": [{"role": "user", "content": "test"}]},
    )

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "upstream_rejected"
    assert "synthetic-sensitive-error-body" not in response.text
