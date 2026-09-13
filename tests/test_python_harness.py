import json
import warnings
from pathlib import Path

import httpx
import pytest
import respx
from conftest import TEST_TOKEN
from openai import PermissionDeniedError
from pydantic import SecretStr

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from fastapi.testclient import TestClient

from clockrouter.config import Settings, load_config
from clockrouter.main import create_app
from examples.python_harness import ClockRouterHarness


def gateway_app(tmp_path: Path):
    return create_app(
        Settings(
            api_token=SecretStr(TEST_TOKEN),
            allowed_projects="private",
            max_request_bytes=16_384,
            max_output_tokens=2_048,
            database_path=tmp_path / "harness-usage.db",
        ),
        load_config(Path("config")),
    )


@respx.mock
def test_prompt_code_crosses_gateway_and_returns_text(tmp_path: Path) -> None:
    upstream = respx.post("http://host.docker.internal:1234/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "local-sdk-response",
                "object": "chat.completion",
                "created": 1,
                "model": "qwen-coder",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": "def answer():\n    return 42",
                        },
                    }
                ],
            },
        )
    )

    with TestClient(gateway_app(tmp_path)) as gateway:
        harness = ClockRouterHarness(
            api_key=TEST_TOKEN,
            base_url="http://testserver/v1",
            http_client=gateway,
        )
        result = harness.prompt_code("Write a tiny answer function")
        trace = harness.last_trace

    assert result == "def answer():\n    return 42"
    assert trace is not None
    assert trace.route == "local-coder"
    assert trace.request_id
    assert trace.latency_ms is not None
    assert upstream.called
    sent = json.loads(upstream.calls.last.request.content)
    assert sent["model"] == "qwen-coder"
    assert sent["messages"][-1]["content"] == "Write a tiny answer function"


@respx.mock
def test_project_scope_is_enforced_before_provider_dispatch(tmp_path: Path) -> None:
    upstream = respx.post("http://host.docker.internal:1234/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={"choices": []})
    )

    with TestClient(gateway_app(tmp_path)) as gateway:
        harness = ClockRouterHarness(
            api_key=TEST_TOKEN,
            base_url="http://testserver/v1",
            project="general",
            http_client=gateway,
        )
        with pytest.raises(PermissionDeniedError):
            harness.prompt_code("This request must be denied")

    assert not upstream.called


def test_harness_requires_a_gateway_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLOCKROUTER_API_TOKEN", raising=False)
    with pytest.raises(ValueError, match="CLOCKROUTER_API_TOKEN"):
        ClockRouterHarness()


def test_harness_rejects_physical_model_names() -> None:
    with pytest.raises(ValueError, match="virtual model"):
        ClockRouterHarness(api_key=TEST_TOKEN, model="qwen-coder")


def test_harness_rejects_blank_prompts() -> None:
    harness = ClockRouterHarness(
        api_key=TEST_TOKEN,
        http_client=httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(500))),
    )
    try:
        with pytest.raises(ValueError, match="prompt must not be blank"):
            harness.prompt_code("   ")
    finally:
        harness.close()
