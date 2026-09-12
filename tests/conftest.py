from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from pydantic import SecretStr

from clockrouter.config import Settings, load_config
from clockrouter.main import create_app

TEST_TOKEN = "clockrouter-test-token-12345"


@pytest_asyncio.fixture
async def application(tmp_path: Path) -> AsyncIterator[FastAPI]:
    app = create_app(
        Settings(
            api_token=SecretStr(TEST_TOKEN),
            allowed_projects="private",
            max_request_bytes=1_024,
            max_output_tokens=100,
            database_path=tmp_path / "usage.db",
        ),
        load_config(Path("config")),
    )
    async with app.router.lifespan_context(app):
        yield app


@pytest_asyncio.fixture
async def client(application: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://clockrouter.test",
    ) as test_client:
        yield test_client


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TEST_TOKEN}"}
