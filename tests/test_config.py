from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError

from clockrouter.config import Config, Settings, load_config


@pytest.mark.parametrize("token", [None, "", "change-me", "short"])
def test_insecure_tokens_are_rejected(token: str | None) -> None:
    settings = Settings(api_token=SecretStr(token) if token is not None else None)

    with pytest.raises(ValueError, match="API_TOKEN"):
        settings.validated_token()


def test_repository_configuration_is_valid() -> None:
    config = load_config(Path("config"))

    assert config.default_project == "private"
    assert config.models["local-coder"].cloud is False


def test_unknown_virtual_target_is_rejected() -> None:
    with pytest.raises(ValidationError, match="unknown target"):
        Config.model_validate(
            {
                "models": {},
                "virtual_models": {"clock/local": {"strategy": "fixed", "target": "missing"}},
                "projects": {"private": {"cloud_allowed": False}},
                "default_project": "private",
            }
        )


def test_cloud_model_requires_https() -> None:
    with pytest.raises(ValidationError, match="HTTPS"):
        Config.model_validate(
            {
                "models": {
                    "cloud": {
                        "provider": "example",
                        "model": "model",
                        "base_url": "http://example.com/v1",
                        "cloud": True,
                    }
                },
                "virtual_models": {"clock/cloud": {"strategy": "fixed", "target": "cloud"}},
                "projects": {"public": {"cloud_allowed": True}},
                "default_project": "public",
            }
        )


def test_cloud_model_requires_pricing() -> None:
    with pytest.raises(ValueError, match="requires pricing"):
        Config.model_validate(
            {
                "models": {
                    "cloud": {
                        "provider": "cloud",
                        "model": "model",
                        "base_url": "https://cloud.example/v1",
                        "cloud": True,
                    }
                },
                "virtual_models": {"clock/cloud": {"strategy": "fixed", "target": "cloud"}},
                "projects": {"general": {"cloud_allowed": True}},
                "default_project": "general",
            }
        )


def test_budget_values_are_loaded_as_exact_decimals() -> None:
    config = load_config(Path("config"))
    assert config.budgets.request_max_usd == Decimal("0.50")
