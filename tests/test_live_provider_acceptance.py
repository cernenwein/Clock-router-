import json
from pathlib import Path

import httpx
import pytest
import respx

from scripts import live_provider_acceptance
from scripts.live_provider_acceptance import ProviderTarget, accept_provider, run_targets


@pytest.mark.parametrize(
    ("provider", "url"),
    [
        ("lmstudio", "http://127.0.0.1:1234/v1"),
        ("ollama", "http://127.0.0.1:11434/v1"),
    ],
)
@respx.mock
def test_accept_provider_runs_all_checks(tmp_path: Path, provider: str, url: str) -> None:
    completion = {
        "id": "synthetic-completion",
        "object": "chat.completion",
        "created": 1,
        "model": "synthetic-model",
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": "CLOCKROUTER_OK"},
            }
        ],
    }
    upstream = respx.post(f"{url}/chat/completions").mock(
        return_value=httpx.Response(200, json=completion)
    )

    def json_request(
        request_url: str,
        *,
        method: str = "GET",
        **kwargs: object,
    ) -> tuple[dict[str, object], dict[str, str]]:
        if request_url == f"{url}/models" and method == "GET":
            return {"data": [{"id": "synthetic-model"}]}, {}
        if request_url == f"{url}/chat/completions" and method == "POST":
            return completion, {}
        raise AssertionError("unexpected direct provider request")

    result = accept_provider(
        ProviderTarget(provider, url),
        timeout=5,
        workspace=tmp_path,
        json_request=json_request,
    )

    assert result == {
        "provider": provider,
        "status": "ok",
        "checks": [
            "models",
            "direct_completion",
            "clock/local",
            "clock/auto",
            "unknown_model_denied",
            "zero_cloud_budget",
        ],
    }
    assert upstream.call_count == 2


def test_failure_report_does_not_disclose_exception_text(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fail(*args: object, **kwargs: object) -> dict[str, object]:
        raise OSError("secret-token at private-host.internal")

    monkeypatch.setattr(live_provider_acceptance, "accept_provider", fail)
    results, failed = run_targets(
        [ProviderTarget("lmstudio", "http://127.0.0.1:1234/v1")],
        timeout=5,
        workspace=tmp_path,
    )
    rendered = json.dumps(results)

    assert failed is True
    assert results == [{"provider": "lmstudio", "status": "failed", "error_type": "OSError"}]
    assert "secret-token" not in rendered
    assert "private-host" not in rendered


def test_runtime_config_is_local_only() -> None:
    target = ProviderTarget("ollama", "http://127.0.0.1:11434/v1")
    config = live_provider_acceptance.build_config(
        target,
        url=target.url,
        model="synthetic-model",
    )

    assert config.models["acceptance-local"].cloud is False
    assert config.models["acceptance-local"].pricing is None
    assert config.projects["private"].cloud_allowed is False


def test_live_runner_rejects_non_loopback_provider_before_network(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="allow-private-network"):
        accept_provider(
            ProviderTarget("lmstudio", "http://provider.example:1234/v1"),
            timeout=5,
            workspace=tmp_path,
        )
