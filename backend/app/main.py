import asyncio
import hmac
import logging
import secrets
import time
from collections import OrderedDict, deque
from contextlib import asynccontextmanager
from threading import Lock

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import Settings, get_settings
from app.ingestion.pipeline import ingest, read_current, restore_snapshot
from app.schemas import ChatRequest, ChatResponse
from app.service import ChatService

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


class RateLimiter:
    def __init__(self, limit: int):
        self.limit = limit
        self.clients = OrderedDict()
        self.lock = Lock()

    def allow(self, key: str) -> bool:
        with self.lock:
            now = time.monotonic()
            queue = self.clients.pop(key, deque())
            while queue and queue[0] < now - 60:
                queue.popleft()
            allowed = len(queue) < self.limit
            if allowed:
                queue.append(now)
            self.clients[key] = queue
            while len(self.clients) > 5000:
                self.clients.popitem(last=False)
            return allowed


def create_app(
    settings: Settings | None = None, service: ChatService | None = None
) -> FastAPI:
    settings = settings or get_settings()
    service = service or ChatService(settings)
    refresh_state = {"status": "idle", "last_completed": None, "error": None}
    refresh_task = None
    limiter = RateLimiter(settings.rate_limit_per_minute)

    @asynccontextmanager
    async def lifespan(app):
        try:
            if (
                read_current(settings.data_dir) is None
                and (settings.data_dir / "snapshot/manifest.json").exists()
            ):
                await asyncio.to_thread(
                    restore_snapshot, settings, settings.data_dir / "snapshot"
                )
            await asyncio.to_thread(service.knowledge.load)
        except Exception:
            logger.warning("knowledge_not_ready")
        yield
        if refresh_task and not refresh_task.done():
            refresh_task.cancel()
        await service.generator.close()

    app = FastAPI(
        title="PlacidWay Knowledge Assistant",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    app.state.service = service
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Authorization"],
    )

    @app.middleware("http")
    async def controls(request: Request, call_next):
        request_id = secrets.token_hex(8)
        try:
            content_length = int(request.headers.get("content-length", "0"))
        except ValueError:
            return JSONResponse({"detail": "Invalid content length"}, status_code=400)
        if content_length > 16_384:
            return JSONResponse({"detail": "Request too large"}, status_code=413)
        if request.method == "POST":
            body = await request.body()
            if len(body) > 16_384:
                return JSONResponse({"detail": "Request too large"}, status_code=413)
        if request.url.path == "/api/chat":
            # Never trust user-controlled forwarding headers. Uvicorn proxy headers
            # are disabled in the deployment command; shared proxies share a limit.
            client = request.client.host if request.client else "unknown"
            if not limiter.allow(client):
                return JSONResponse(
                    {"detail": "Please wait before sending more questions."},
                    status_code=429,
                    headers={"Retry-After": "60"},
                )
        started = time.monotonic()
        try:
            response = await call_next(request)
        except Exception:
            logger.error("request_failed id=%s", request_id)
            response = JSONResponse(
                {"detail": "The request could not be completed."}, status_code=503
            )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )
        response.headers["X-Request-ID"] = request_id
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        logger.info(
            "request id=%s method=%s status=%s elapsed_ms=%d",
            request_id,
            request.method,
            response.status_code,
            int((time.monotonic() - started) * 1000),
        )
        return response

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return JSONResponse(
            {"detail": exc.detail}, status_code=exc.status_code, headers=exc.headers
        )

    # FastAPI's default validation errors echo invalid input; suppress it for privacy.
    from fastapi.exceptions import RequestValidationError

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        return JSONResponse(
            {
                "detail": "Invalid request. Enter a question of 1–1500 characters and a valid conversation ID."
            },
            status_code=422,
        )

    @app.get("/api/health")
    async def health():
        knowledge = await asyncio.to_thread(service.knowledge.status)
        return {
            "status": "ok" if knowledge["ready"] else "degraded",
            "knowledge_ready": knowledge["ready"],
            "generation_available": settings.generation_enabled
            or settings.answer_mode == "extractive",
            "answer_mode": settings.answer_mode,
            "gemini_configured": settings.generation_enabled,
            "model": settings.gemini_model
            if settings.answer_mode == "gemini"
            else None,
        }

    @app.get("/api/knowledge/status")
    async def knowledge_status():
        status = await asyncio.to_thread(service.knowledge.status)
        status["sources"] = [
            {
                k: value
                for k, value in source.items()
                if k
                in (
                    "id",
                    "title",
                    "category",
                    "url",
                    "status",
                    "ingested_at",
                    "chunk_count",
                )
            }
            for source in status["sources"]
        ]
        return status

    @app.post("/api/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest):
        try:
            async with asyncio.timeout(40):
                return await service.chat(request)
        except TimeoutError:
            raise HTTPException(
                status_code=503, detail="The request timed out. Please try again later."
            )

    async def admin(authorization: str | None = Header(default=None)):
        expected = settings.admin_api_key.get_secret_value()
        supplied = (
            authorization[7:]
            if authorization and authorization.startswith("Bearer ")
            else ""
        )
        if len(expected) < 32 or not hmac.compare_digest(supplied, expected):
            raise HTTPException(
                status_code=401, detail="Administrator authorization required"
            )

    async def refresh():
        try:
            # Run the complete pipeline in a worker thread: embeddings and Chroma
            # work must not block chat's event loop.
            result = await asyncio.to_thread(lambda: asyncio.run(ingest(settings)))
            await asyncio.to_thread(service.knowledge.load)
            refresh_state.update(
                status="completed", last_completed=result["created_at"], error=None
            )
        except Exception:
            logger.warning("refresh_failed_previous_index_retained")
            refresh_state.update(
                status="failed",
                error="Refresh failed; previous working index retained.",
            )

    @app.post("/api/admin/refresh", dependencies=[Depends(admin)], status_code=202)
    async def start_refresh():
        nonlocal refresh_task
        if refresh_task and not refresh_task.done():
            raise HTTPException(status_code=409, detail="A refresh is already running")
        refresh_state.update(status="running", error=None)
        refresh_task = asyncio.create_task(refresh())
        return {
            "status": "accepted",
            "persistence": "Runtime data may be ephemeral. Export and redeploy a snapshot for durable hosting refresh.",
        }

    @app.get("/api/admin/refresh", dependencies=[Depends(admin)])
    async def refresh_status():
        return refresh_state

    @app.get("/api/admin/unanswered", dependencies=[Depends(admin)])
    async def unanswered():
        return {
            "records": service.unanswered.read(),
            "privacy": "Only constrained topic metadata is logged; raw questions are not retained.",
        }

    if settings.serve_frontend and settings.frontend_dir.exists():
        app.mount(
            "/",
            StaticFiles(directory=str(settings.frontend_dir), html=True),
            name="frontend",
        )
    return app


app = create_app()
