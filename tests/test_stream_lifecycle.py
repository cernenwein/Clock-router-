import asyncio
from pathlib import Path

import httpx
import pytest
import respx

from clockrouter.main import proxy_upstream_stream

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "providers"
UPSTREAM_URL = "http://host.docker.internal:1234/v1/chat/completions"


class RecordingStream(httpx.AsyncByteStream):
    def __init__(self, chunks: list[bytes]) -> None:
        self.chunks = chunks
        self.closed = False

    async def __aiter__(self):
        for chunk in self.chunks:
            yield chunk

    async def aclose(self) -> None:
        self.closed = True


class BlockingStream(httpx.AsyncByteStream):
    def __init__(self) -> None:
        self.waiting = asyncio.Event()
        self.closed = False

    async def __aiter__(self):
        yield b'data: {"choices":[]}\n\n'
        self.waiting.set()
        await asyncio.Event().wait()

    async def aclose(self) -> None:
        self.closed = True


class FailingRecordingStream(httpx.AsyncByteStream):
    def __init__(self) -> None:
        self.closed = False

    async def __aiter__(self):
        yield b'data: {"choices":[]}\n\n'
        raise httpx.ReadError("synthetic-sensitive-stream-error")

    async def aclose(self) -> None:
        self.closed = True


class CancelledRecordingStream(httpx.AsyncByteStream):
    def __init__(self) -> None:
        self.closed = False

    async def __aiter__(self):
        raise asyncio.CancelledError
        yield b""  # pragma: no cover - keeps this an async generator

    async def aclose(self) -> None:
        self.closed = True


def streaming_response(stream: httpx.AsyncByteStream) -> httpx.Response:
    return httpx.Response(
        200,
        stream=stream,
        headers={"content-type": "text/event-stream"},
        request=httpx.Request("POST", UPSTREAM_URL),
    )


async def test_completed_stream_closes_without_appending_an_error() -> None:
    event = (FIXTURE_DIR / "completion.sse").read_bytes()
    stream = RecordingStream([event[:17], event[17:83], event[83:]])
    content = b"".join([chunk async for chunk in proxy_upstream_stream(streaming_response(stream))])

    assert content == event
    assert stream.closed is True


async def test_truncated_stream_appends_sanitized_terminal_error_and_closes() -> None:
    partial = b'data: {"choices":[{"delta":{"content":"partial"}}]}\n\n'
    stream = RecordingStream([partial])
    content = b"".join([chunk async for chunk in proxy_upstream_stream(streaming_response(stream))])

    assert content.startswith(partial)
    assert b"upstream_stream_incomplete" in content
    assert content.endswith(b"data: [DONE]\n\n")
    assert stream.closed is True


async def test_downstream_cancellation_propagates_and_closes_upstream() -> None:
    stream = BlockingStream()
    chunks = proxy_upstream_stream(streaming_response(stream))
    assert await anext(chunks) == b'data: {"choices":[]}\n\n'
    pending = asyncio.create_task(anext(chunks))
    await stream.waiting.wait()
    pending.cancel()

    with pytest.raises(asyncio.CancelledError):
        await pending

    assert stream.closed is True


async def test_upstream_stream_failure_is_sanitized_and_closed() -> None:
    stream = FailingRecordingStream()
    content = b"".join([chunk async for chunk in proxy_upstream_stream(streaming_response(stream))])

    assert b"upstream_stream_failed" in content
    assert b"synthetic-sensitive-stream-error" not in content
    assert content.endswith(b"data: [DONE]\n\n")
    assert stream.closed is True


async def test_upstream_cancellation_propagates_and_closes_response() -> None:
    stream = CancelledRecordingStream()
    chunks = proxy_upstream_stream(streaming_response(stream))

    with pytest.raises(asyncio.CancelledError):
        await anext(chunks)

    assert stream.closed is True


@respx.mock
async def test_non_sse_success_is_rejected_and_closed(
    client: httpx.AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    upstream = httpx.Response(
        200,
        text="synthetic-sensitive-stream",
        headers={"content-type": "text/plain"},
    )
    respx.post(UPSTREAM_URL).mock(return_value=upstream)

    response = await client.post(
        "/v1/chat/completions",
        headers=auth_headers,
        json={
            "model": "clock/local",
            "stream": True,
            "messages": [{"role": "user", "content": "test"}],
        },
    )

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "invalid_upstream_response"
    assert "synthetic-sensitive-stream" not in response.text
    assert upstream.is_closed
