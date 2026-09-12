import asyncio
import json
import secrets
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, Header, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import ValidationError

from clockrouter.config import Config, Settings, load_config
from clockrouter.routing import RoutingError, select_route
from clockrouter.schemas import ChatCompletionRequest, error_payload


@dataclass(frozen=True)
class ClientIdentity:
    projects: frozenset[str]


class AuthenticationError(Exception):
    def __init__(self, request_id: str):
        self.request_id = request_id


def api_error(
    status_code: int,
    message: str,
    error_type: str,
    code: str,
    request_id: str,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=error_payload(message, error_type, code),
        headers={"X-ClockRouter-Request-ID": request_id},
    )


async def read_bounded_body(request: Request, limit: int) -> bytes | None:
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > limit:
            return None
        chunks.append(chunk)
    return b"".join(chunks)


def create_app(
    runtime_settings: Settings | None = None,
    runtime_config: Config | None = None,
) -> FastAPI:
    settings = runtime_settings or Settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        application.state.api_token = settings.validated_token()
        application.state.allowed_projects = settings.project_scope()
        application.state.config = runtime_config or load_config(settings.config_dir)
        unknown_scopes = (
            application.state.allowed_projects - application.state.config.projects.keys()
        )
        if unknown_scopes:
            names = ", ".join(sorted(unknown_scopes))
            raise ValueError(f"credential scope references unknown projects: {names}")
        application.state.settings = settings
        application.state.client = httpx.AsyncClient(
            timeout=settings.request_timeout_seconds,
            trust_env=False,
        )
        yield
        await application.state.client.aclose()

    application = FastAPI(title="ClockRouter", version="0.2.0", lifespan=lifespan)

    def require_token(
        request: Request,
        authorization: str | None = Header(default=None),
    ) -> ClientIdentity:
        expected = f"Bearer {request.app.state.api_token}"
        if authorization is None or not secrets.compare_digest(authorization, expected):
            raise AuthenticationError(str(uuid.uuid4()))
        return ClientIdentity(projects=request.app.state.allowed_projects)

    @application.exception_handler(AuthenticationError)
    async def authentication_error(_request: Request, exc: AuthenticationError) -> JSONResponse:
        return api_error(
            401,
            "Invalid ClockRouter API token",
            "authentication_error",
            "invalid_api_key",
            exc.request_id,
        )

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "clockrouter"}

    @application.get("/v1/models")
    async def models(
        request: Request,
        _identity: Annotated[ClientIdentity, Depends(require_token)],
    ) -> dict:
        data = [
            {"id": name, "object": "model", "owned_by": "clockrouter"}
            for name in request.app.state.config.virtual_models
        ]
        return {"object": "list", "data": data}

    @application.post("/v1/chat/completions")
    async def chat_completions(
        request: Request,
        identity: Annotated[ClientIdentity, Depends(require_token)],
        x_clockrouter_project: str | None = Header(default=None),
    ):
        started = time.monotonic()
        request_id = str(uuid.uuid4())
        raw_body = await read_bounded_body(request, settings.max_request_bytes)
        if raw_body is None:
            return api_error(
                413,
                "Request body is too large",
                "invalid_request_error",
                "request_too_large",
                request_id,
            )
        try:
            payload = json.loads(raw_body)
            body = ChatCompletionRequest.model_validate(payload)
        except (json.JSONDecodeError, UnicodeDecodeError, ValidationError, TypeError):
            return api_error(
                400,
                "Invalid Chat Completions request",
                "invalid_request_error",
                "invalid_request",
                request_id,
            )
        if body.max_tokens is not None and body.max_tokens > settings.max_output_tokens:
            return api_error(
                400,
                "Requested output token limit exceeds policy",
                "invalid_request_error",
                "max_tokens_exceeded",
                request_id,
            )

        project = x_clockrouter_project or request.app.state.config.default_project
        if project not in identity.projects:
            return api_error(
                403,
                "Credential is not authorized for this project",
                "permission_error",
                "project_not_allowed",
                request_id,
            )
        try:
            route = select_route(request.app.state.config, body.model, project)
        except RoutingError:
            return api_error(
                400,
                "Requested model or project cannot be routed",
                "invalid_request_error",
                "route_not_found",
                request_id,
            )

        upstream_body = body.model_dump(mode="json", exclude_none=True)
        upstream_body["model"] = route.upstream_model
        upstream_url = f"{route.base_url}/chat/completions"
        headers = {"Content-Type": "application/json", "X-Request-ID": request_id}

        if body.stream:
            return await stream_completion(
                request, upstream_url, headers, upstream_body, route.name, request_id
            )

        try:
            upstream = await request.app.state.client.post(
                upstream_url, headers=headers, json=upstream_body
            )
        except httpx.TimeoutException:
            return api_error(
                504, "Upstream model timed out", "upstream_error", "upstream_timeout", request_id
            )
        except httpx.RequestError:
            return api_error(
                502,
                "Upstream model is unavailable",
                "upstream_error",
                "upstream_unavailable",
                request_id,
            )
        if upstream.is_error:
            return api_error(
                502,
                "Upstream model returned an error",
                "upstream_error",
                "upstream_rejected",
                request_id,
            )
        try:
            content = upstream.json()
        except ValueError:
            return api_error(
                502,
                "Upstream model returned an invalid response",
                "upstream_error",
                "invalid_upstream_response",
                request_id,
            )

        response = JSONResponse(status_code=upstream.status_code, content=content)
        response.headers["X-ClockRouter-Request-ID"] = request_id
        response.headers["X-ClockRouter-Route"] = route.name
        response.headers["X-ClockRouter-Latency-MS"] = str(
            round((time.monotonic() - started) * 1000)
        )
        return response

    return application


async def stream_completion(
    request: Request,
    upstream_url: str,
    headers: dict[str, str],
    upstream_body: dict,
    route_name: str,
    request_id: str,
):
    try:
        upstream_request = request.app.state.client.build_request(
            "POST", upstream_url, headers=headers, json=upstream_body
        )
        upstream = await request.app.state.client.send(upstream_request, stream=True)
    except httpx.TimeoutException:
        return api_error(
            504, "Upstream model timed out", "upstream_error", "upstream_timeout", request_id
        )
    except httpx.RequestError:
        return api_error(
            502,
            "Upstream model is unavailable",
            "upstream_error",
            "upstream_unavailable",
            request_id,
        )
    if upstream.is_error:
        await upstream.aclose()
        return api_error(
            502,
            "Upstream model returned an error",
            "upstream_error",
            "upstream_rejected",
            request_id,
        )

    async def chunks():
        try:
            async for chunk in upstream.aiter_bytes():
                yield chunk
        except httpx.HTTPError:
            event = error_payload(
                "Upstream stream failed", "upstream_error", "upstream_stream_failed"
            )
            yield f"data: {json.dumps(event, separators=(',', ':'))}\n\ndata: [DONE]\n\n".encode()
        except asyncio.CancelledError:
            raise
        finally:
            await upstream.aclose()

    return StreamingResponse(
        chunks(),
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type", "text/event-stream"),
        headers={"X-ClockRouter-Request-ID": request_id, "X-ClockRouter-Route": route_name},
    )


app = create_app()
