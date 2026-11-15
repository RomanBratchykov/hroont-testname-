"""Two-endpoint localhost API, with optional serving of the built frontend."""

import asyncio
import contextlib
import hashlib
import json
import logging
import secrets
from contextlib import asynccontextmanager
from typing import Literal
from urllib.parse import urlsplit

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, model_validator
from starlette.middleware.trustedhost import TrustedHostMiddleware

from backend.config import ROOT, Settings
from backend.documents import Attachment, extract
from backend.field_data import check_sources, climate
from backend.orchestrator import Orchestrator
from backend.providers import Provider
from backend.profile import ProfileUpdate
from backend.store import Conflict, SessionCapacity, Store
from backend.tools import build_tools, rag_health

log = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["send", "list", "read", "rename", "delete", "clear", "profile", "save_profile", "clear_profile"] = "send"
    conversation_id: str = Field(
        default="", max_length=100, pattern=r"^[A-Za-z0-9_-]*$"
    )
    request_id: str = Field(default="", max_length=100, pattern=r"^[A-Za-z0-9_-]*$")
    message: str = Field(default="", max_length=16000)
    mode: Literal["auto", "fast", "thinking"] = "auto"
    title: str = Field(default="", max_length=100)
    files: list[Attachment] = Field(default_factory=list, max_length=3)
    profile: ProfileUpdate | None = None

    @model_validator(mode="after")
    def required_fields(self):
        if (
            self.action in {"send", "read", "rename", "delete"}
            and not self.conversation_id
        ):
            raise ValueError("conversation_id is required.")
        if self.action == "send" and (
            not self.request_id or (not self.message.strip() and not self.files)
        ):
            raise ValueError("Sending requires request_id and message or files.")
        if self.action == "rename" and not self.title.strip():
            raise ValueError("Title must not be blank.")
        return self


def create_app(config: Settings | None = None, transport=None) -> FastAPI:
    config = config or Settings.from_env()
    store = Store(config.database_path)
    active: dict[str, asyncio.Task] = {}

    @asynccontextmanager
    async def lifespan(app):
        store.recover()
        async with httpx.AsyncClient(
            transport=transport, follow_redirects=False, trust_env=False
        ) as http:
            app.state.data_http = http
            app.state.data_slots = asyncio.Semaphore(2)
            app.state.engine = Orchestrator(
                config,
                store,
                Provider(config, http),
                build_tools(
                    store, config, data_http=http, data_slots=app.state.data_slots
                ),
            )

            async def cleanup():
                while True:
                    await asyncio.sleep(60)
                    store.expire()

            janitor = asyncio.create_task(cleanup())
            try:
                yield
            finally:
                janitor.cancel()
                for task in list(active.values()):
                    task.cancel()
                await asyncio.gather(
                    janitor, *list(active.values()), return_exceptions=True
                )

    app = FastAPI(
        title="AgroResilience local orchestrator",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    allowed_hosts = ["localhost", "127.0.0.1", "[::1]", "testserver"]
    if config.public_origin:
        allowed_hosts.append(urlsplit(config.public_origin).hostname)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

    @app.middleware("http")
    async def local_requests(request, call_next):
        origin = request.headers.get("origin")
        if origin:
            parsed = urlsplit(origin)
            local_origin = parsed.scheme == "http" and parsed.hostname in {
                "localhost",
                "127.0.0.1",
                "::1",
            }
            if not local_origin and origin != config.public_origin:
                return JSONResponse(
                    {"detail": "This browser origin is not allowed."},
                    status_code=403,
                )
        if request.method == "POST":
            if (
                request.headers.get("content-type", "").split(";")[0]
                != "application/json"
            ):
                return JSONResponse(
                    {"detail": "Use application/json."}, status_code=415
                )
            body = bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > 15 * 1024 * 1024:
                    return JSONResponse(
                        {"detail": "Request exceeds 15 MB."}, status_code=413
                    )
            request._body = bytes(body)
        guest_token = None
        if request.url.path == "/api/chat" and request.method == "POST":
            guest_token = request.cookies.get("croptato_guest", "")
            if len(guest_token) != 43 or not all(
                char.isalnum() or char in "-_" for char in guest_token
            ):
                guest_token = secrets.token_urlsafe(32)
            owner = hashlib.sha256(guest_token.encode()).hexdigest()
            try:
                store.admit_guest(
                    owner, config.max_active_users if config.provider == "deepseek" else None
                )
            except SessionCapacity as exc:
                return JSONResponse(
                    {"detail": str(exc)}, status_code=429, headers={"Retry-After": "60"}
                )
            request.state.owner = owner
        response = await call_next(request)
        if guest_token:
            response.set_cookie(
                "croptato_guest",
                guest_token,
                httponly=True,
                secure=bool(config.public_origin)
                and request.headers.get("host", "").split(":")[0]
                == urlsplit(config.public_origin).hostname,
                samesite="lax",
                max_age=30 * 86400,
                path="/",
            )
        return response

    @app.get("/api/health")
    async def health():
        retrieval = await asyncio.to_thread(rag_health, config.rag_url)
        return {
            "status": "ok",
            "provider": config.provider,
            "model": config.model_name,
            "workspace": "private-guest",
            "max_active_users": config.max_active_users if config.provider == "deepseek" else None,
            "active": app.state.engine.active,
            "capacity": config.concurrency,
            "phase": config.phase,
            "budget": {
                **store.budget(config.phase),
                "limit_usd": float(config.phase_budget),
            },
            "configured": config.provider == "ollama"
            or (not config.paid_model)
            or bool(config.api_key and config.input_rate and config.output_rate),
            "scientific_tools": [],
            "scientific_analysis": "unavailable",
            "climate_retrieval": "available",
            "data_tools": ["get_climate_history", "check_data_sources"],
            "retrieval": retrieval,
            "rag_configured": bool(config.rag_url),
            "translation_configured": bool(config.translation_url),
        }

    @app.get("/api/field-data")
    async def field_data(
        latitude: float = Query(ge=-85, le=85, allow_inf_nan=False),
        longitude: float = Query(ge=-180, le=180, allow_inf_nan=False),
    ):
        async with app.state.data_slots:
            return await climate(
                app.state.data_http,
                config.database_path.parent / "dashboard-cache.sqlite",
                latitude,
                longitude,
            )

    @app.get("/api/data-sources")
    async def data_sources(
        latitude: float = Query(ge=-85, le=85, allow_inf_nan=False),
        longitude: float = Query(ge=-180, le=180, allow_inf_nan=False),
    ):
        async with app.state.data_slots:
            return await check_sources(
                app.state.data_http, latitude, longitude,
                earthdata_token=config.earthdata_token,
            )

    @app.post("/api/chat")
    async def chat(payload: ChatRequest, request: Request):
        store.expire()
        owner = request.state.owner
        if payload.action == "profile":
            return store.profile(owner)
        if payload.action == "clear_profile":
            return store.clear_profile(owner)
        if payload.action == "save_profile":
            if payload.profile is None:
                raise HTTPException(422, "Provide profile facts or a field boundary.")
            try:
                return store.update_profile(owner, payload.profile.model_dump())
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from exc
        if payload.action == "list":
            return {"conversations": store.list_chats(owner)}
        if payload.conversation_id:
            existing = store.read(payload.conversation_id)
            if (payload.action != "send" or existing is not None) and not store.owns(
                payload.conversation_id, owner
            ):
                raise HTTPException(404, "Chat not found.")
        if payload.action == "read":
            result = store.read(payload.conversation_id)
            if result is None:
                raise HTTPException(404, "Chat not found.")
            return result
        if payload.action in {"delete", "clear"}:
            identifiers = [
                identifier
                for identifier in list(active)
                if store.owns(
                    (store.run_record(identifier) or {}).get("conversation_id"), owner
                )
                and (
                    payload.action == "clear"
                    or (store.run_record(identifier) or {}).get("conversation_id")
                    == payload.conversation_id
                )
            ]
            tasks = [
                active[identifier] for identifier in identifiers if identifier in active
            ]
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            store.delete(
                None if payload.action == "clear" else payload.conversation_id, owner
            )
            return {"status": "deleted"}
        if payload.action == "rename":
            if not store.rename(payload.conversation_id, payload.title.strip()):
                raise HTTPException(404, "Chat not found.")
            return {"status": "renamed"}
        try:
            extracted = await asyncio.to_thread(
                lambda: "".join(extract(file) for file in payload.files)
            )
        except Exception as exc:
            # Parser exception details may contain private input; expose only actionable safe text.
            detail = (
                str(exc)
                if isinstance(exc, ValueError)
                else "Could not parse the attachment."
            )
            raise HTTPException(422, detail) from exc
        content = payload.message.strip() + extracted
        if len(content.encode()) > 24000:
            raise HTTPException(
                422,
                "Combined message/file text exceeds 24 KB. Supply smaller excerpts.",
            )
        try:
            previous = store.begin(
                payload.conversation_id,
                payload.request_id,
                content,
                payload.mode,
                [file.name for file in payload.files],
                owner=owner,
            )
        except PermissionError as exc:
            raise HTTPException(404, "Chat not found.") from exc
        except Conflict as exc:
            raise HTTPException(409, str(exc)) from exc
        if previous and previous["status"] in {"queued", "running"}:
            raise HTTPException(409, "This request is already processing.")

        async def stream():
            task = None
            try:
                if previous:
                    event = (
                        json.loads(previous["result"])
                        if previous["result"]
                        else {
                            "type": "error",
                            "code": previous["status"],
                            "message": "This turn was interrupted. Send a new message to retry.",
                        }
                    )
                    yield json.dumps(event) + "\n"
                    return
                queue = asyncio.Queue()

                async def produce():
                    try:
                        async for event in app.state.engine.run(
                            payload.conversation_id,
                            payload.request_id,
                            content,
                            payload.mode,
                            payload.files,
                        ):
                            await queue.put(event)
                    except asyncio.CancelledError:
                        raise
                    except Exception as exc:  # noqa: BLE001 — isolate unexpected failures without exposing private input.
                        log.error(
                            "orchestrator_failed request=%s category=%s",
                            payload.request_id,
                            type(exc).__name__,
                        )
                        event = {
                            "type": "error",
                            "code": "failed",
                            "message": "Processing failed. Retry or check the local server.",
                        }
                        store.finish(payload.request_id, event, "failed")
                        await queue.put(event)
                    finally:
                        await queue.put(None)

                task = asyncio.create_task(produce())
                active[payload.request_id] = task
                while True:
                    if await request.is_disconnected():
                        break
                    try:
                        event = await asyncio.wait_for(queue.get(), timeout=0.25)
                    except TimeoutError:
                        continue
                    if event is None:
                        break
                    yield json.dumps(event) + "\n"
            finally:
                if task:
                    task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await task
                    active.pop(payload.request_id, None)
                if not previous:
                    store.finish(
                        payload.request_id,
                        {
                            "type": "error",
                            "code": "cancelled",
                            "message": "Turn cancelled.",
                        },
                        "cancelled",
                    )

        return StreamingResponse(
            stream(),
            media_type="application/x-ndjson",
            headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
        )

    dist = ROOT / "frontend/dist"
    if dist.exists():
        app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
    return app
