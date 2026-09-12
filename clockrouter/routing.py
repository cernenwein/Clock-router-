from dataclasses import dataclass

from clockrouter.config import Config


class RoutingError(ValueError):
    pass


@dataclass(frozen=True)
class Route:
    name: str
    provider: str
    upstream_model: str
    base_url: str
    cloud: bool
    reason: str


def select_route(config: Config, requested_model: str, project: str) -> Route:
    policy = config.projects.get(project)
    if policy is None:
        raise RoutingError(f"Unknown project policy: {project}")

    virtual = config.virtual_models.get(requested_model)
    if virtual is None:
        raise RoutingError(f"Unknown virtual model: {requested_model}")

    strategy = virtual.strategy
    if strategy == "fixed":
        target = virtual.target
        reason = f"fixed route requested by {requested_model}"
    elif strategy == "auto":
        local_names = [name for name, item in config.models.items() if not item.cloud]
        if not local_names:
            raise RoutingError("No local model is configured")
        target = local_names[0]
        reason = "v0.1 deterministic auto route"
    else:
        raise RoutingError(f"Unsupported routing strategy: {strategy}")

    model = config.models.get(target)
    if model is None:
        raise RoutingError(f"Route target is not configured: {target}")

    cloud = model.cloud
    if cloud and not policy.cloud_allowed:
        raise RoutingError(f"Cloud routing prohibited for project: {project}")

    return Route(
        name=target,
        provider=model.provider,
        upstream_model=model.model,
        base_url=str(model.base_url).rstrip("/"),
        cloud=cloud,
        reason=reason,
    )
