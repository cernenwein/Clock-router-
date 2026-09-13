#!/usr/bin/env python3
"""Run sanitized live acceptance against LM Studio and Ollama."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import tempfile
import warnings
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openai import BadRequestError
from pydantic import SecretStr

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from fastapi.testclient import TestClient

from clockrouter.config import Config, ModelConfig, ProjectPolicy, Settings, VirtualModelConfig
from clockrouter.main import create_app
from examples.python_harness import ClockRouterHarness
from scripts.local_provider_harness import request_json, select_model, validate_local_url

SYNTHETIC_PROMPT = "Reply with exactly CLOCKROUTER_OK"
JsonRequest = Callable[..., tuple[dict[str, Any], dict[str, str]]]


@dataclass(frozen=True)
class ProviderTarget:
    name: str
    url: str
    model: str | None = None
    api_key: str | None = None


def build_config(target: ProviderTarget, *, url: str, model: str) -> Config:
    return Config(
        models={
            "acceptance-local": ModelConfig(
                provider=target.name,
                model=model,
                base_url=url,
                cloud=False,
            )
        },
        virtual_models={
            "clock/local": VirtualModelConfig(strategy="fixed", target="acceptance-local"),
            "clock/auto": VirtualModelConfig(strategy="auto"),
        },
        projects={"private": ProjectPolicy(cloud_allowed=False)},
        default_project="private",
    )


def require_choices(payload: dict[str, Any]) -> None:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise TypeError("completion response does not contain choices")


def accept_provider(
    target: ProviderTarget,
    *,
    timeout: float,
    workspace: Path,
    json_request: JsonRequest = request_json,
) -> dict[str, Any]:
    url = validate_local_url(target.url, allow_private_network=False)
    headers = {"Authorization": f"Bearer {target.api_key}"} if target.api_key else {}
    models, _ = json_request(f"{url}/models", headers=headers, timeout=timeout)
    model = select_model(models, target.model)

    direct, _ = json_request(
        f"{url}/chat/completions",
        method="POST",
        payload={
            "model": model,
            "messages": [{"role": "user", "content": SYNTHETIC_PROMPT}],
            "max_tokens": 32,
        },
        headers=headers,
        timeout=timeout,
    )
    require_choices(direct)

    token = secrets.token_urlsafe(24)
    app = create_app(
        Settings(
            api_token=SecretStr(token),
            allowed_projects="private",
            max_output_tokens=64,
            database_path=workspace / f"{target.name}-usage.db",
            request_timeout_seconds=timeout,
        ),
        build_config(target, url=url, model=model),
    )
    checks = ["models", "direct_completion"]
    with TestClient(app) as gateway:
        harness = ClockRouterHarness(
            api_key=token,
            base_url="http://testserver/v1",
            timeout=timeout,
            http_client=gateway,
        )
        for virtual_model in ("clock/local", "clock/auto"):
            harness.prompt_code(SYNTHETIC_PROMPT, model=virtual_model, max_tokens=32)
            if harness.last_trace is None or harness.last_trace.route != "acceptance-local":
                raise RuntimeError("gateway did not report the expected local route")
            checks.append(virtual_model)

        try:
            harness.prompt_code(SYNTHETIC_PROMPT, model="clock/missing", max_tokens=32)
        except BadRequestError:
            checks.append("unknown_model_denied")
        else:
            raise RuntimeError("unknown virtual model was not denied")

        if app.state.ledger.total_microusd() != 0:
            raise RuntimeError("local acceptance request changed the cloud budget ledger")
        checks.append("zero_cloud_budget")

    return {"provider": target.name, "status": "ok", "checks": checks}


def run_targets(
    targets: list[ProviderTarget],
    *,
    timeout: float,
    workspace: Path,
) -> tuple[list[dict[str, Any]], bool]:
    results: list[dict[str, Any]] = []
    failed = False
    for target in targets:
        try:
            result = accept_provider(
                target,
                timeout=timeout,
                workspace=workspace,
            )
        # This is the output-sanitization boundary: report the exception class,
        # never provider URLs, credentials, prompts, or response bodies.
        except Exception as exc:  # noqa: BLE001
            failed = True
            result = {
                "provider": target.name,
                "status": "failed",
                "error_type": type(exc).__name__,
            }
        results.append(result)
    return results, failed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lmstudio-url", default="http://127.0.0.1:1234/v1")
    parser.add_argument("--lmstudio-model")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434/v1")
    parser.add_argument("--ollama-model")
    parser.add_argument("--timeout", type=float, default=120)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    targets = [
        ProviderTarget(
            "lmstudio",
            args.lmstudio_url,
            args.lmstudio_model,
            os.getenv("LMSTUDIO_API_KEY"),
        ),
        ProviderTarget(
            "ollama",
            args.ollama_url,
            args.ollama_model,
            os.getenv("OLLAMA_API_KEY"),
        ),
    ]
    with tempfile.TemporaryDirectory(prefix="clockrouter-acceptance-") as directory:
        results, failed = run_targets(
            targets,
            timeout=args.timeout,
            workspace=Path(directory),
        )
    print(json.dumps({"status": "failed" if failed else "ok", "providers": results}))
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"status": "failed", "error_type": type(exc).__name__}))
        raise SystemExit(1) from None
