from clockrouter.config import Config
from clockrouter.routing import RoutingError, select_route


def config() -> Config:
    return Config(
        models={
            "local": {
                "provider": "lmstudio",
                "model": "qwen",
                "base_url": "http://local/v1",
                "cloud": False,
            },
            "premium": {
                "provider": "openrouter",
                "model": "premium",
                "base_url": "https://example.invalid/v1",
                "cloud": True,
            },
        },
        virtual_models={
            "clock/local": {"strategy": "fixed", "target": "local"},
            "clock/smart": {"strategy": "fixed", "target": "premium"},
            "clock/auto": {"strategy": "auto"},
        },
        projects={
            "private": {"cloud_allowed": False},
            "public": {"cloud_allowed": True},
        },
        default_project="private",
    )


def test_auto_prefers_local() -> None:
    route = select_route(config(), "clock/auto", "public")
    assert route.name == "local"
    assert not route.cloud


def test_private_project_blocks_cloud() -> None:
    try:
        select_route(config(), "clock/smart", "private")
    except RoutingError as exc:
        assert "prohibited" in str(exc)
    else:
        raise AssertionError("private project unexpectedly routed to cloud")
