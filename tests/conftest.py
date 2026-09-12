from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from pydantic import SecretStr

from clockrouter.config import Settings, load_config
from clockrouter.main import create_app

TEST_TOKEN = "clockrouter-test-token-12345"


@pytest_asyncio.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(
        Settings(
            api_token=SecretStr(TEST_TOKEN),
            allowed_projects="private",
            max_request_bytes=1_024,
            max_output_tokens=100,
        ),
        load_config(Path("config")),
    )
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://clockrouter.test",
        ) as test_client:
            yield test_client


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TEST_TOKEN}"}
