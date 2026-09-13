from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from decimal import Decimal
from pathlib import Path

import httpx
import pytest
from conftest import TEST_TOKEN
from pydantic import SecretStr

from clockrouter.config import (
    Config,
    ModelConfig,
    PriceConfig,
    ProjectPolicy,
    Settings,
    VirtualModelConfig,
)
from clockrouter.main import create_app
from clockrouter.providers import ProviderCall


class RecordingAdapter:
    def __init__(self, *, fails: bool = False) -> None:
        self.calls: list[ProviderCall] = []
        self.fails = fails

    async def complete(self, client: httpx.AsyncClient, call: ProviderCall) -> httpx.Response:
        self.calls.append(call)
        if self.fails:
            request = httpx.Request("POST", "http://provider.example/v1/chat/completions")
            raise httpx.ConnectError("synthetic-sensitive-transport-detail", request=request)
        return httpx.Response(
            200,
            json={"id": "synthetic-response", "choices": []},
            request=httpx.Request("POST", "http://provider.example/v1/chat/completions"),
        )

    async def stream(self, client: httpx.AsyncClient, call: ProviderCall) -> httpx.Response:
        raise AssertionError("stream dispatch was not expected")


def local_config(provider: str, *, adapter: str = "recording") -> Config:
    return Config(
        models={
            "local": ModelConfig(
                provider=provider,
                adapter=adapter,
                model="synthetic-model",
                base_url="http://provider.example/v1",
            )
        },
        virtual_models={"clock/local": VirtualModelConfig(strategy="fixed", target="local")},
        projects={"private": ProjectPolicy(cloud_allowed=False)},
        default_project="private",
    )


@asynccontextmanager
async def request_app(
    tmp_path: Path,
    config: Config,
    adapters: dict[str, RecordingAdapter],
) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(
        Settings(
            api_token=SecretStr(TEST_TOKEN),
            allowed_projects="private",
            database_path=tmp_path / "usage.db",
        ),
        config,
        provider_adapters=adapters,
    )
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://clockrouter.test",
        ) as client,
    ):
        yield client


@pytest.mark.parametrize("provider", ["lmstudio", "ollama"])
async def test_provider_brand_does_not_select_transport(tmp_path: Path, provider: str) -> None:
    adapter = RecordingAdapter()
    async with request_app(tmp_path, local_config(provider), {"recording": adapter}) as client:
        response = await client.post(
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
            json={"model": "clock/local", "messages": [{"role": "user", "content": "test"}]},
        )

    assert response.status_code == 200
    assert len(adapter.calls) == 1
    assert adapter.calls[0].upstream_model == "synthetic-model"


async def test_unavailable_adapter_fails_during_startup(tmp_path: Path) -> None:
    app = create_app(
        Settings(
            api_token=SecretStr(TEST_TOKEN),
            allowed_projects="private",
            database_path=tmp_path / "usage.db",
        ),
        local_config("synthetic-provider", adapter="missing"),
        provider_adapters={"recording": RecordingAdapter()},
    )

    with pytest.raises(ValueError, match="unavailable provider adapters: missing"):
        async with app.router.lifespan_context(app):
            pass


async def test_invalid_adapter_object_fails_during_startup(tmp_path: Path) -> None:
    app = create_app(
        Settings(
            api_token=SecretStr(TEST_TOKEN),
            allowed_projects="private",
            database_path=tmp_path / "usage.db",
        ),
        local_config("synthetic-provider"),
        provider_adapters={"recording": object()},  # type: ignore[dict-item]
    )

    with pytest.raises(TypeError, match="invalid provider adapters: recording"):
        async with app.router.lifespan_context(app):
            pass


async def test_local_failure_does_not_dispatch_cloud_adapter(tmp_path: Path) -> None:
    local = RecordingAdapter(fails=True)
    cloud = RecordingAdapter()
    config = Config(
        models={
            "local": ModelConfig(
                provider="synthetic-local",
                adapter="local-adapter",
                model="local-model",
                base_url="http://provider.example/v1",
            ),
            "cloud": ModelConfig(
                provider="synthetic-cloud",
                adapter="cloud-adapter",
                model="cloud-model",
                base_url="https://cloud.example/v1",
                cloud=True,
                pricing=PriceConfig(
                    input_usd_per_million=Decimal(1),
                    output_usd_per_million=Decimal(1),
                ),
            ),
        },
        virtual_models={"clock/auto": VirtualModelConfig(strategy="auto")},
        projects={"private": ProjectPolicy(cloud_allowed=False)},
        default_project="private",
    )

    async with request_app(
        tmp_path,
        config,
        {"local-adapter": local, "cloud-adapter": cloud},
    ) as client:
        response = await client.post(
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
            json={"model": "clock/auto", "messages": [{"role": "user", "content": "test"}]},
        )

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "upstream_unavailable"
    assert "synthetic-sensitive" not in response.text
    assert len(local.calls) == 1
    assert cloud.calls == []
