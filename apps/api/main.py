"""
FinScan AI: FastAPI Application Entrypoint.

Serves REST API and mounts React SPA from apps/ui/dist.
"""

import logging
import os
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from apps.api.auth.deps import get_current_user
from apps.api.routes.applications import router as applications_router
from apps.api.routes.documents import router as documents_router
from apps.api.routes.review import router as review_router
from apps.api.routes.uploads import router as uploads_router
from apps.api.routes.auth import router as auth_router
from apps.api.middleware.rate_limit import close_redis_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    _warm_rag_index()
    yield
    await close_redis_client()


def _warm_rag_index() -> None:
    """
    Eagerly loads the shared policy RAG index once per worker process, instead
    of leaving it to load lazily on that worker's first /questions request.
    Without this, whichever underwriter's question happens to land on a
    freshly-started gunicorn worker pays the full policy-corpus parse/embed
    cost inline with their request - worse right after every deploy, when
    every worker is cold at once. Failure here must never block startup: the
    lazy path in apps/api/routes/review.py still loads it correctly later.
    """
    try:
        from core.rag.indexer import get_default_index_manager
        from apps.api.routes.review import _resolve_policy_dir

        get_default_index_manager().load_policy_corpus(policy_dir=_resolve_policy_dir())
    except Exception:
        logging.getLogger("finscan.api.startup").warning(
            "RAG policy index warmup failed; will load lazily on first /questions call.",
            exc_info=True,
        )


app = FastAPI(
    title="FinScan AI API",
    version="1.0.0",
    description="Deterministic code decides. AI explains. A human approves.",
    lifespan=lifespan,
)

def _cors_origins() -> list[str]:
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    domain = os.getenv("DOMAIN_NAME", "").strip()
    if domain and domain != "localhost":
        origins.extend([
            f"http://{domain}",
            f"https://{domain}",
            f"http://www.{domain}",
            f"https://www.{domain}",
        ])
    extra = os.getenv("CORS_ORIGINS", "").strip()
    if extra:
        for o in extra.split(","):
            cleaned = o.strip()
            if cleaned and cleaned != "*":
                origins.append(cleaned)
    return origins


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_origin_regex=os.getenv("CORS_ORIGIN_REGEX", r"https?://.*\.vercel\.app"),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Every dossier route carries applicant PII, so all of them sit behind a
# verified session. AUTH_MODE=mock keeps get_current_user a passthrough, so
# local/demo/test flows stay open; google/required enforce 401/403 here.
AUTHENTICATED = [Depends(get_current_user)]

app.include_router(auth_router)
app.include_router(applications_router, dependencies=AUTHENTICATED)
app.include_router(documents_router, dependencies=AUTHENTICATED)
app.include_router(review_router, dependencies=AUTHENTICATED)
app.include_router(uploads_router, dependencies=AUTHENTICATED)


@app.get("/health", tags=["Health"])
async def health_check():
    """Liveness: the process is up and serving. Dependencies: see /health/ready."""
    from apps.api.config import settings

    return {
        "status": "ok",
        "service": "finscan-api",
        "version": settings.RELEASE_VERSION,
        "git_sha": settings.GIT_SHA,
        "build_timestamp": settings.BUILD_TIMESTAMP,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health/ready", tags=["Health"])
async def readiness_check():
    """
    Readiness: reports `degraded` when Postgres or Redis is unreachable, so a
    probe (and the UI's connectivity banner) can tell a live API apart from a
    working system. /health stays a pure liveness signal.
    """
    from sqlalchemy import text

    from apps.api.config import settings
    from apps.api.db.session import async_session_factory
    from apps.api.middleware.rate_limit import get_redis_client

    checks: dict[str, str] = {}

    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as db_err:  # noqa: BLE001 - probe must never raise
        checks["database"] = f"unavailable: {type(db_err).__name__}"

    try:
        redis_client = await get_redis_client()
        if redis_client is None:
            checks["redis"] = "not_configured"
        else:
            await redis_client.ping()
            # Local dev silently substitutes FakeRedis; say so rather than
            # reporting a rate-limiter/spend-guard that isn't really shared.
            checks["redis"] = (
                "in_memory_fallback"
                if type(redis_client).__module__.startswith("fakeredis")
                else "ok"
            )
    except Exception as redis_err:  # noqa: BLE001 - probe must never raise
        checks["redis"] = f"unavailable: {type(redis_err).__name__}"

    degraded = [name for name, value in checks.items() if value.startswith("unavailable")]

    return {
        "status": "degraded" if degraded else "ok",
        "service": "finscan-api",
        "checks": checks,
        "version": settings.RELEASE_VERSION,
        "environment": settings.ENVIRONMENT,
    }


# Mount built React SPA in same-origin mode if dist exists
ui_dist_path = os.path.join(os.path.dirname(__file__), "../ui/dist")
if os.path.exists(ui_dist_path):
    app.mount("/", StaticFiles(directory=ui_dist_path, html=True), name="ui")
