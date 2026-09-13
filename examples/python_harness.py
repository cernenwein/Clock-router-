"""Minimal coding-harness client for ClockRouter's OpenAI-compatible API."""

from __future__ import annotations

import argparse
import os
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Self

import httpx
from openai import OpenAI


@dataclass(frozen=True)
class ClockRouterTrace:
    """Non-sensitive routing evidence returned in ClockRouter headers."""

    request_id: str | None
    route: str | None
    latency_ms: int | None


class ClockRouterHarness:
    """Send coding prompts through ClockRouter without choosing a provider."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = "http://127.0.0.1:4000/v1",
        model: str = "clock/local",
        project: str = "private",
        timeout: float = 120,
        max_retries: int = 0,
        http_client: httpx.Client | None = None,
    ) -> None:
        token = api_key or os.getenv("CLOCKROUTER_API_TOKEN")
        if not token:
            raise ValueError("set CLOCKROUTER_API_TOKEN or pass api_key")
        if not project.strip():
            raise ValueError("project must not be blank")
        if not model.startswith("clock/"):
            raise ValueError("model must be a ClockRouter virtual model")

        self.model = model
        self.project = project
        self.last_trace: ClockRouterTrace | None = None
        self._client = OpenAI(
            api_key=token,
            base_url=f"{base_url.rstrip('/')}/",
            default_headers={"X-ClockRouter-Project": project},
            timeout=timeout,
            max_retries=max_retries,
            http_client=http_client,
        )

    def prompt_code(
        self,
        prompt: str,
        *,
        model: str | None = None,
        system_prompt: str = "You are a careful software engineering assistant.",
        max_tokens: int = 1024,
    ) -> str:
        """Return assistant text while ClockRouter handles provider selection."""
        if not prompt.strip():
            raise ValueError("prompt must not be blank")
        requested_model = model or self.model
        if not requested_model.startswith("clock/"):
            raise ValueError("model must be a ClockRouter virtual model")

        raw_response = self._client.chat.completions.with_raw_response.create(
            model=requested_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
        )
        response = raw_response.parse()
        latency = raw_response.headers.get("X-ClockRouter-Latency-MS")
        self.last_trace = ClockRouterTrace(
            request_id=raw_response.headers.get("X-ClockRouter-Request-ID"),
            route=raw_response.headers.get("X-ClockRouter-Route"),
            latency_ms=int(latency) if latency is not None else None,
        )

        if not response.choices or response.choices[0].message.content is None:
            raise RuntimeError("ClockRouter response did not contain assistant text")
        return response.choices[0].message.content

    def stream_code(
        self,
        prompt: str,
        *,
        model: str | None = None,
        system_prompt: str = "You are a careful software engineering assistant.",
        max_tokens: int = 1024,
    ) -> Iterator[str]:
        """Yield assistant-text fragments from ClockRouter's streaming API."""
        if not prompt.strip():
            raise ValueError("prompt must not be blank")
        requested_model = model or self.model
        if not requested_model.startswith("clock/"):
            raise ValueError("model must be a ClockRouter virtual model")

        stream = self._client.chat.completions.create(
            model=requested_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
            stream=True,
        )
        try:
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        finally:
            stream.close()

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prompt", help="Synthetic or approved coding prompt")
    parser.add_argument(
        "--base-url",
        default=os.getenv("CLOCKROUTER_BASE_URL", "http://127.0.0.1:4000/v1"),
    )
    parser.add_argument("--model", default="clock/local")
    parser.add_argument("--project", default="private")
    args = parser.parse_args()

    with ClockRouterHarness(
        base_url=args.base_url,
        model=args.model,
        project=args.project,
    ) as harness:
        print(harness.prompt_code(args.prompt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
