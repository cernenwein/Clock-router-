import json

import httpx
import respx


async def test_health_does_not_require_authentication(client: httpx.AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "clockrouter"}


async def test_models_rejects_missing_token(client: httpx.AsyncClient) -> None:
    response = await client.get("/v1/models")

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid ClockRouter API token"}


async def test_models_lists_only_virtual_models(
    client: httpx.AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.get("/v1/models", headers=auth_headers)

    assert response.status_code == 200
    assert {model["id"] for model in response.json()["data"]} == {
        "clock/local",
        "clock/auto",
    }


async def test_unknown_project_fails_closed(
    client: httpx.AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.post(
        "/v1/chat/completions",
        headers={**auth_headers, "X-ClockRouter-Project": "not-configured"},
        json={"model": "clock/auto", "messages": [{"role": "user", "content": "hello"}]},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Unknown project policy: not-configured"}


@respx.mock
async def test_chat_rewrites_virtual_model_and_reports_route(
    client: httpx.AsyncClient, auth_headers: dict[str, str]
) -> None:
    upstream = respx.post(
        "http://host.docker.internal:1234/v1/chat/completions"
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "local-response",
                "object": "chat.completion",
                "choices": [{"index": 0, "message": {"role": "assistant", "content": "hi"}}],
            },
        )
    )

    response = await client.post(
        "/v1/chat/completions",
        headers=auth_headers,
        json={"model": "clock/auto", "messages": [{"role": "user", "content": "hello"}]},
    )

    assert response.status_code == 200
    assert response.json()["id"] == "local-response"
    assert response.headers["x-clockrouter-route"] == "local-coder"
    assert response.headers["x-clockrouter-request-id"]
    assert int(response.headers["x-clockrouter-latency-ms"]) >= 0
    assert upstream.called
    sent = json.loads(upstream.calls.last.request.content)
    assert sent["model"] == "qwen-coder"


@respx.mock
async def test_streaming_chat_proxies_sse_bytes(
    client: httpx.AsyncClient, auth_headers: dict[str, str]
) -> None:
    event = b'data: {"choices":[{"delta":{"content":"tick"}}]}\n\ndata: [DONE]\n\n'
    upstream = respx.post(
        "http://host.docker.internal:1234/v1/chat/completions"
    ).mock(
        return_value=httpx.Response(
            200,
            content=event,
            headers={"content-type": "text/event-stream"},
        )
    )

    async with client.stream(
        "POST",
        "/v1/chat/completions",
        headers=auth_headers,
        json={
            "model": "clock/local",
            "stream": True,
            "messages": [{"role": "user", "content": "hello"}],
        },
    ) as response:
        content = b"".join([chunk async for chunk in response.aiter_bytes()])

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["x-clockrouter-route"] == "local-coder"
    assert content == event
    assert upstream.called
