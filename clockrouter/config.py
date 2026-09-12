from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    api_token: SecretStr | None = None
    allowed_projects: str = "private"
    config_dir: Path = Path("config")
    request_timeout_seconds: float = Field(default=120, gt=0, le=600)
    max_request_bytes: int = Field(default=1_048_576, ge=1_024, le=20_971_520)
    max_output_tokens: int = Field(default=32_768, ge=1, le=1_000_000)
    database_path: Path = Path("data/clockrouter.db")

    model_config = SettingsConfigDict(env_prefix="CLOCKROUTER_", env_file=".env")

    def validated_token(self) -> str:
        token = self.api_token.get_secret_value().strip() if self.api_token else ""
        if token.lower() in {"", "change-me", "changeme", "replace-me"} or len(token) < 16:
            raise ValueError(
                "CLOCKROUTER_API_TOKEN must be at least 16 characters and not a placeholder"
            )
        return token

    def project_scope(self) -> frozenset[str]:
        projects = frozenset(
            item.strip() for item in self.allowed_projects.split(",") if item.strip()
        )
        if not projects:
            raise ValueError("CLOCKROUTER_ALLOWED_PROJECTS must contain at least one project")
        return projects


class PriceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    input_usd_per_million: Decimal = Field(ge=0)
    output_usd_per_million: Decimal = Field(ge=0)


class ModelConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    base_url: HttpUrl
    cloud: bool = False
    pricing: PriceConfig | None = None

    @model_validator(mode="after")
    def require_tls_for_cloud(self) -> "ModelConfig":
        if self.cloud and self.base_url.scheme != "https":
            raise ValueError("cloud model base_url must use HTTPS")
        if self.cloud and self.pricing is None:
            raise ValueError("cloud model requires pricing")
        return self


class VirtualModelConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    strategy: Literal["fixed", "auto"]
    target: str | None = None

    @model_validator(mode="after")
    def validate_target(self) -> "VirtualModelConfig":
        if self.strategy == "fixed" and not self.target:
            raise ValueError("fixed virtual model requires a target")
        if self.strategy == "auto" and self.target is not None:
            raise ValueError("auto virtual model cannot define a target")
        return self


class ProjectPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cloud_allowed: bool = False


class BudgetConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_max_usd: Decimal = Field(default=Decimal("0.50"), ge=0)
    daily_usd: Decimal = Field(default=Decimal("2.00"), ge=0)
    monthly_usd: Decimal = Field(default=Decimal("30.00"), ge=0)


class Config(BaseModel):
    model_config = ConfigDict(extra="forbid")
    models: dict[str, ModelConfig]
    virtual_models: dict[str, VirtualModelConfig]
    projects: dict[str, ProjectPolicy]
    default_project: str
    budgets: BudgetConfig = Field(default_factory=BudgetConfig)

    @model_validator(mode="after")
    def validate_references(self) -> "Config":
        if self.default_project not in self.projects:
            raise ValueError("default_project must reference a configured project")
        for name, virtual in self.virtual_models.items():
            if virtual.target is not None and virtual.target not in self.models:
                raise ValueError(
                    f"virtual model {name!r} references unknown target {virtual.target!r}"
                )
        if any(item.strategy == "auto" for item in self.virtual_models.values()) and not any(
            not item.cloud for item in self.models.values()
        ):
            raise ValueError("auto routing requires at least one local model")
        return self


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise TypeError(f"configuration root must be a mapping: {path}")
    return data


def load_config(directory: Path) -> Config:
    model_data = _read_yaml(directory / "models.yaml")
    policy_data = _read_yaml(directory / "policies.yaml")
    budget_data = _read_yaml(directory / "budgets.yaml")
    return Config.model_validate(
        {
            "models": model_data.get("models", {}),
            "virtual_models": model_data.get("virtual_models", {}),
            "projects": policy_data.get("projects", {}),
            "default_project": policy_data.get("default_project", "private"),
            "budgets": budget_data.get("budgets", {}).get("global", {}),
        }
    )
