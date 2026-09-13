import json
from decimal import Decimal
from pathlib import Path

import httpx
import respx
from conftest import TEST_TOKEN
from fastapi import FastAPI
from pydantic import SecretStr

from clockrouter.config import (
    BudgetConfig,
    Config,
    ModelConfig,
    PriceConfig,
    ProjectPolicy,
    Settings,
    VirtualModelConfig,
)
from clockrouter.main import create_app


class FailingStream(httpx.AsyncByteStream):
    async def __aiter__(self):
        yield b'data: {"choices":[{"delta":{"content":"partial"}}]}\n\n'
        raise httpx.ReadError("sensitive upstream failure")


def cloud_config(*, request_max_usd: Decimal) -> Config:
    return Config(
        models={
            "cloud": ModelConfig(
                provider="test-cloud",
                model="cloud-model",
                base_url="https://cloud.example/v1",
                cloud=True,
                pricing=PriceConfig(
                    input_usd_per_million=Decimal(1),
                    output_usd_per_million=Decimal(2),
                ),
            )
        },
        virtual_models={"clock/cloud": VirtualModelConfig(strategy="fixed", target="cloud")},
        projects={"general": ProjectPolicy(cloud_allowed=True)},
        default_project="general",
        budgets=BudgetConfig(
            request_max_usd=request_max_usd,
            daily_usd=Decimal(10),
            monthly_usd=Decimal(100),
        ),
    )


def test_settings_default_database_is_local_file() -> None:
    assert Settings().database_path == Path("data/clockrouter.db")


async def test_health_does_not_require_authentication(client: httpx.AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "clockrouter"}


async def test_models_rejects_missing_token(client: httpx.AsyncClient) -> None:
    response = await client.get("/v1/models")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_api_key"
    assert response.headers["x-clockrouter-request-id"]


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
    assert response.json()["error"]["code"] == "project_not_allowed"


async def test_known_but_unscoped_project_is_forbidden(
    client: httpx.AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.post(
        "/v1/chat/completions",
        headers={**auth_headers, "X-ClockRouter-Project": "general"},
        json={"model": "clock/auto", "messages": [{"role": "user", "content": "hello"}]},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "project_not_allowed"


async def test_malformed_request_is_rejected(
    client: httpx.AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.post(
        "/v1/chat/completions",
        headers={**auth_headers, "Content-Type": "application/json"},
        content=b"not-json",
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_request"


async def test_request_size_is_bounded(
    client: httpx.AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.post(
        "/v1/chat/completions",
        headers=auth_headers,
        content=b"x" * 1_025,
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "request_too_large"


async def test_output_tokens_are_bounded(
    client: httpx.AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.post(
        "/v1/chat/completions",
        headers=auth_headers,
        json={
            "model": "clock/auto",
            "messages": [{"role": "user", "content": "hello"}],
            "max_tokens": 101,
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "max_tokens_exceeded"


@respx.mock
async def test_chat_rewrites_virtual_model_and_reports_route(
    client: httpx.AsyncClient, auth_headers: dict[str, str]
) -> None:
    upstream = respx.post("http://host.docker.internal:1234/v1/chat/completions").mock(
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
async def test_local_route_does_not_reserve_cloud_budget(
    client: httpx.AsyncClient,
    application: FastAPI,
    auth_headers: dict[str, str],
) -> None:
    respx.post("http://host.docker.internal:1234/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={"id": "local", "choices": []})
    )
    response = await client.post(
        "/v1/chat/completions",
        headers=auth_headers,
        json={"model": "clock/local", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert response.status_code == 200
    assert application.state.ledger.total_microusd() == 0


@respx.mock
async def test_cloud_budget_denial_happens_before_dispatch(tmp_path: Path) -> None:
    upstream = respx.post("https://cloud.example/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={"id": "must-not-run"})
    )
    app = create_app(
        Settings(
            api_token=SecretStr(TEST_TOKEN),
            allowed_projects="general",
            max_output_tokens=100,
            database_path=tmp_path / "usage.db",
        ),
        cloud_config(request_max_usd=Decimal(0)),
    )
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://clockrouter.test"
        ) as cloud_client,
    ):
        response = await cloud_client.post(
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
            json={
                "model": "clock/cloud",
                "max_tokens": 1,
                "messages": [{"role": "user", "content": "hi"}],
            },
        )
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "budget_exceeded"
    assert not upstream.called


@respx.mock
async def test_cloud_usage_reconciles_the_reservation(tmp_path: Path) -> None:
    respx.post("https://cloud.example/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "cloud-result",
                "choices": [],
                "usage": {"prompt_tokens": 3, "completion_tokens": 4},
            },
        )
    )
    app = create_app(
        Settings(
            api_token=SecretStr(TEST_TOKEN),
            allowed_projects="general",
            max_output_tokens=100,
            database_path=tmp_path / "usage.db",
        ),
        cloud_config(request_max_usd=Decimal(1)),
    )
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://clockrouter.test"
        ) as cloud_client:
            response = await cloud_client.post(
                "/v1/chat/completions",
                headers={"Authorization": f"Bearer {TEST_TOKEN}"},
                json={
                    "model": "clock/cloud",
                    "max_tokens": 1,
                    "messages": [{"role": "user", "content": "hi"}],
                },
            )
        charged = app.state.ledger.total_microusd()
    assert response.status_code == 200
    assert charged == 11


@respx.mock
async def test_streaming_chat_proxies_sse_bytes(
    client: httpx.AsyncClient, auth_headers: dict[str, str]
) -> None:
    event = b'data: {"choices":[{"delta":{"content":"tick"}}]}\n\ndata: [DONE]\n\n'
    upstream = respx.post("http://host.docker.internal:1234/v1/chat/completions").mock(
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


@respx.mock
async def test_upstream_error_body_is_not_disclosed(
    client: httpx.AsyncClient, auth_headers: dict[str, str]
) -> None:
    respx.post("http://host.docker.internal:1234/v1/chat/completions").mock(
        return_value=httpx.Response(500, text="secret prompt echoed here")
    )

    response = await client.post(
        "/v1/chat/completions",
        headers=auth_headers,
        json={"model": "clock/auto", "messages": [{"role": "user", "content": "hello"}]},
    )

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "upstream_rejected"
    assert "secret prompt" not in response.text


@respx.mock
async def test_invalid_upstream_json_is_sanitized(
    client: httpx.AsyncClient, auth_headers: dict[str, str]
) -> None:
    respx.post("http://host.docker.internal:1234/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            text="not-json",
            headers={"content-type": "application/json"},
        )
    )

    response = await client.post(
        "/v1/chat/completions",
        headers=auth_headers,
        json={"model": "clock/auto", "messages": [{"role": "user", "content": "hello"}]},
    )

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "invalid_upstream_response"


@respx.mock
async def test_upstream_connection_failure_is_sanitized(
    client: httpx.AsyncClient, auth_headers: dict[str, str]
) -> None:
    respx.post("http://host.docker.internal:1234/v1/chat/completions").mock(
        side_effect=httpx.ConnectError("private network details")
    )

    response = await client.post(
        "/v1/chat/completions",
        headers=auth_headers,
        json={"model": "clock/auto", "messages": [{"role": "user", "content": "hello"}]},
    )

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "upstream_unavailable"
    assert "private network" not in response.text


@respx.mock
async def test_upstream_timeout_is_sanitized(
    client: httpx.AsyncClient, auth_headers: dict[str, str]
) -> None:
    respx.post("http://host.docker.internal:1234/v1/chat/completions").mock(
        side_effect=httpx.ReadTimeout("private timeout details")
    )

    response = await client.post(
        "/v1/chat/completions",
        headers=auth_headers,
        json={"model": "clock/auto", "messages": [{"role": "user", "content": "hello"}]},
    )

    assert response.status_code == 504
    assert response.json()["error"]["code"] == "upstream_timeout"
    assert "private timeout" not in response.text


@respx.mock
async def test_midstream_failure_emits_sanitized_sse_error(
    client: httpx.AsyncClient, auth_headers: dict[str, str]
) -> None:
    respx.post("http://host.docker.internal:1234/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            stream=FailingStream(),
            headers={"content-type": "text/event-stream"},
        )
    )

    async with client.stream(
        "POST",
        "/v1/chat/completions",
        headers=auth_headers,
        json={
            "model": "clock/auto",
            "stream": True,
            "messages": [{"role": "user", "content": "hello"}],
        },
    ) as response:
        content = b"".join([chunk async for chunk in response.aiter_bytes()])

    assert response.status_code == 200
    assert b"partial" in content
    assert b"upstream_stream_failed" in content
    assert b"sensitive upstream failure" not in content
