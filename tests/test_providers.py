import json

import httpx

from clockrouter.providers import OpenAICompatibleAdapter, ProviderCall, default_adapters


class SyntheticStream(httpx.AsyncByteStream):
    async def __aiter__(self):
        yield b"data: [DONE]\n\n"


async def test_openai_compatible_completion_builds_expected_request() -> None:
    requests: list[httpx.Request] = []

    async def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"id": "synthetic-response"})

    payload = {
        "model": "clock/local",
        "messages": [{"role": "user", "content": "synthetic"}],
    }
    call = ProviderCall(
        base_url="http://provider.example/v1",
        upstream_model="synthetic-model",
        request_id="synthetic-request-id",
        payload=payload,
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        response = await OpenAICompatibleAdapter().complete(client, call)

    assert response.status_code == 200
    assert len(requests) == 1
    request = requests[0]
    assert str(request.url) == "http://provider.example/v1/chat/completions"
    assert request.headers["x-request-id"] == "synthetic-request-id"
    assert request.headers["content-type"] == "application/json"
    assert json.loads(request.content) == {
        "model": "synthetic-model",
        "messages": [{"role": "user", "content": "synthetic"}],
    }
    assert payload["model"] == "clock/local"


async def test_openai_compatible_stream_uses_unread_streaming_response() -> None:
    requests: list[httpx.Request] = []

    async def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            stream=SyntheticStream(),
            headers={"content-type": "text/event-stream"},
        )

    call = ProviderCall(
        base_url="http://provider.example/v1/",
        upstream_model="synthetic-model",
        request_id="synthetic-request-id",
        payload={"model": "clock/local", "messages": [], "stream": True},
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        response = await OpenAICompatibleAdapter().stream(client, call)
        assert response.is_closed is False
        assert await response.aread() == b"data: [DONE]\n\n"
        await response.aclose()

    assert len(requests) == 1
    assert str(requests[0].url) == "http://provider.example/v1/chat/completions"
    assert json.loads(requests[0].content)["model"] == "synthetic-model"


def test_default_registry_contains_only_openai_compatible_adapter() -> None:
    adapters = default_adapters()

    assert set(adapters) == {"openai-compatible"}
    assert isinstance(adapters["openai-compatible"], OpenAICompatibleAdapter)
