import secrets
import time
import uuid
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from clockrouter.config import Settings, load_config
from clockrouter.routing import RoutingError, select_route

settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.config = load_config(settings.config_dir)
    app.state.client = httpx.AsyncClient(
        timeout=settings.request_timeout_seconds,
        trust_env=False,
    )
    yield
    await app.state.client.aclose()


app = FastAPI(title="ClockRouter", version="0.1.0", lifespan=lifespan)


def require_token(authorization: str | None = Header(default=None)) -> None:
    expected = f"Bearer {settings.api_token}"
    if authorization is None or not secrets.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Invalid ClockRouter API token")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "clockrouter"}


@app.get("/v1/models", dependencies=[Depends(require_token)])
async def models(request: Request) -> dict:
    data = [
        {"id": name, "object": "model", "owned_by": "clockrouter"}
        for name in request.app.state.config.virtual_models
    ]
    return {"object": "list", "data": data}


@app.post("/v1/chat/completions", dependencies=[Depends(require_token)])
async def chat_completions(
    request: Request,
    x_clockrouter_project: str | None = Header(default=None),
):
    started = time.monotonic()
    request_id = str(uuid.uuid4())
    body = await request.json()
    requested_model = body.get("model", "clock/auto")
    project = x_clockrouter_project or request.app.state.config.default_project

    try:
        route = select_route(request.app.state.config, requested_model, project)
    except RoutingError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    upstream_body = {**body, "model": route.upstream_model}
    upstream_url = f"{route.base_url}/chat/completions"
    headers = {"Content-Type": "application/json", "X-Request-ID": request_id}

    if body.get("stream", False):
        upstream_request = request.app.state.client.build_request(
            "POST", upstream_url, headers=headers, json=upstream_body
        )
        upstream = await request.app.state.client.send(upstream_request, stream=True)
        if upstream.is_error:
            content = await upstream.aread()
            await upstream.aclose()
            return JSONResponse(
                status_code=upstream.status_code, content={"detail": content.decode()}
            )

        async def chunks():
            try:
                async for chunk in upstream.aiter_bytes():
                    yield chunk
            finally:
                await upstream.aclose()

        return StreamingResponse(
            chunks(),
            status_code=upstream.status_code,
            media_type=upstream.headers.get("content-type", "text/event-stream"),
            headers={"X-ClockRouter-Request-ID": request_id, "X-ClockRouter-Route": route.name},
        )

    upstream = await request.app.state.client.post(
        upstream_url, headers=headers, json=upstream_body
    )
    response = JSONResponse(status_code=upstream.status_code, content=upstream.json())
    response.headers["X-ClockRouter-Request-ID"] = request_id
    response.headers["X-ClockRouter-Route"] = route.name
    response.headers["X-ClockRouter-Latency-MS"] = str(round((time.monotonic() - started) * 1000))
    return response
