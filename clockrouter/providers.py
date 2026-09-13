from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

import httpx


@dataclass(frozen=True)
class ProviderCall:
    base_url: str
    upstream_model: str
    request_id: str
    payload: dict[str, Any]


@runtime_checkable
class ProviderAdapter(Protocol):
    async def complete(
        self,
        client: httpx.AsyncClient,
        call: ProviderCall,
    ) -> httpx.Response: ...

    async def stream(
        self,
        client: httpx.AsyncClient,
        call: ProviderCall,
    ) -> httpx.Response: ...


class OpenAICompatibleAdapter:
    @staticmethod
    def _request_parts(call: ProviderCall) -> tuple[str, dict[str, str], dict[str, Any]]:
        payload = {**call.payload, "model": call.upstream_model}
        headers = {"Content-Type": "application/json", "X-Request-ID": call.request_id}
        url = f"{call.base_url.rstrip('/')}/chat/completions"
        return url, headers, payload

    async def complete(
        self,
        client: httpx.AsyncClient,
        call: ProviderCall,
    ) -> httpx.Response:
        url, headers, payload = self._request_parts(call)
        return await client.post(url, headers=headers, json=payload)

    async def stream(
        self,
        client: httpx.AsyncClient,
        call: ProviderCall,
    ) -> httpx.Response:
        url, headers, payload = self._request_parts(call)
        request = client.build_request("POST", url, headers=headers, json=payload)
        return await client.send(request, stream=True)


def default_adapters() -> dict[str, ProviderAdapter]:
    return {"openai-compatible": OpenAICompatibleAdapter()}
