from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    api_token: str = "change-me"
    config_dir: Path = Path("config")
    request_timeout_seconds: float = 120

    model_config = SettingsConfigDict(env_prefix="CLOCKROUTER_", env_file=".env")


@dataclass(frozen=True)
class Config:
    models: dict[str, dict[str, Any]]
    virtual_models: dict[str, dict[str, Any]]
    projects: dict[str, dict[str, Any]]
    default_project: str


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_config(directory: Path) -> Config:
    model_data = _read_yaml(directory / "models.yaml")
    policy_data = _read_yaml(directory / "policies.yaml")
    return Config(
        models=model_data.get("models", {}),
        virtual_models=model_data.get("virtual_models", {}),
        projects=policy_data.get("projects", {}),
        default_project=policy_data.get("default_project", "private"),
    )
