#!/usr/bin/env python3
"""Smoke-test a local OpenAI-compatible provider through ClockRouter."""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlsplit

DEFAULT_PROVIDER_URLS = {
    "lmstudio": "http://127.0.0.1:1234/v1",
    "ollama": "http://127.0.0.1:11434/v1",
}
SAFE_HOSTS = {"localhost", "127.0.0.1", "::1", "host.docker.internal"}


def validate_local_url(value: str, *, allow_private_network: bool) -> str:
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("URL must be an absolute HTTP(S) URL")
    host = parsed.hostname.lower()
    if host in SAFE_HOSTS:
        return value.rstrip("/")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        if allow_private_network:
            return value.rstrip("/")
        raise ValueError(
            "non-loopback host requires --allow-private-network; use only a trusted LAN or overlay"
        ) from None
    if allow_private_network and (address.is_private or address.is_link_local):
        return value.rstrip("/")
    raise ValueError("public provider and gateway addresses are not permitted by this harness")


def select_model(payload: dict[str, Any], requested: str | None) -> str:
    data = payload.get("data")
    if not isinstance(data, list):
        raise ValueError("provider /v1/models response does not contain a data list")
    model_ids = [
        item.get("id")
        for item in data
        if isinstance(item, dict) and isinstance(item.get("id"), str) and item["id"]
    ]
    if not model_ids:
        raise ValueError("provider reports no models; load or pull a model first")
    if requested is not None:
        if requested not in model_ids:
            raise ValueError(f"requested upstream model is unavailable: {requested}")
        return requested
    return model_ids[0]


def request_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 120,
) -> tuple[dict[str, Any], dict[str, str]]:
    body = json.dumps(payload).encode() if payload is not None else None
    request_headers = {"Accept": "application/json", **(headers or {})}
    if body is not None:
        request_headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            content = json.loads(response.read())
            return content, dict(response.headers.items())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"{method} {url} returned HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"{method} {url} could not connect") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{method} {url} returned invalid JSON") from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=sorted(DEFAULT_PROVIDER_URLS), required=True)
    parser.add_argument("--provider-url")
    parser.add_argument("--provider-model")
    parser.add_argument("--provider-api-key")
    parser.add_argument("--gateway-url", default="http://127.0.0.1:4000")
    parser.add_argument("--gateway-token", default=os.getenv("CLOCKROUTER_API_TOKEN"))
    parser.add_argument("--project", default="private")
    parser.add_argument("--virtual-model", default="clock/local")
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--list-only", action="store_true")
    parser.add_argument("--allow-private-network", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    provider_url = validate_local_url(
        args.provider_url or DEFAULT_PROVIDER_URLS[args.provider],
        allow_private_network=args.allow_private_network,
    )
    provider_headers = {}
    if args.provider_api_key:
        provider_headers["Authorization"] = f"Bearer {args.provider_api_key}"
    models, _ = request_json(
        f"{provider_url}/models", headers=provider_headers, timeout=args.timeout
    )
    model = select_model(models, args.provider_model)
    if args.list_only:
        print(json.dumps({"provider": args.provider, "selected_model": model}))
        return 0
    if not args.gateway_token:
        raise ValueError("set CLOCKROUTER_API_TOKEN or pass --gateway-token")
    gateway_url = validate_local_url(
        args.gateway_url, allow_private_network=args.allow_private_network
    )
    health, _ = request_json(f"{gateway_url}/health", timeout=args.timeout)
    if health.get("status") != "ok":
        raise RuntimeError("ClockRouter health check did not report ok")
    result, response_headers = request_json(
        f"{gateway_url}/v1/chat/completions",
        method="POST",
        payload={
            "model": args.virtual_model,
            "messages": [{"role": "user", "content": "Reply with exactly CLOCKROUTER_OK"}],
            "max_tokens": 32,
        },
        headers={
            "Authorization": f"Bearer {args.gateway_token}",
            "X-ClockRouter-Project": args.project,
        },
        timeout=args.timeout,
    )
    choices = result.get("choices")
    if not isinstance(choices, list):
        raise RuntimeError("gateway response does not contain a choices list")
    print(
        json.dumps(
            {
                "provider": args.provider,
                "provider_model": model,
                "gateway_route": response_headers.get("X-ClockRouter-Route"),
                "request_id": response_headers.get("X-ClockRouter-Request-ID"),
                "status": "ok",
            }
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError) as exc:
        print(f"harness failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
