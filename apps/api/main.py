"""
FinScan AI: FastAPI Application Entrypoint.

Serves REST API and mounts React SPA from apps/ui/dist.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from apps.api.routes.applications import router as applications_router
from apps.api.routes.documents import router as documents_router
from apps.api.routes.review import router as review_router
from apps.api.routes.uploads import router as uploads_router
from apps.api.routes.auth import router as auth_router
from apps.api.middleware.rate_limit import close_redis_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_redis_client()


app = FastAPI(
    title="FinScan AI API",
    version="1.0.0",
    description="Deterministic code decides. AI explains. A human approves.",
    lifespan=lifespan,
)

def _cors_origins() -> list[str]:
    domain = os.getenv("DOMAIN_NAME", "").strip()
    if domain and domain != "localhost":
        return [f"https://{domain}", f"https://www.{domain}"]
    # Local/dev same-origin (Vite proxy); explicit, no wildcard+credentials.
    return ["http://localhost:3000", "http://127.0.0.1:3000"]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register route modules
app.include_router(auth_router)
app.include_router(applications_router)
app.include_router(documents_router)
app.include_router(review_router)
app.include_router(uploads_router)


@app.get("/health", tags=["Health"])
async def health_check():
    from apps.api.config import settings
    return {
        "status": "ok",
        "service": "finscan-api",
        "version": settings.RELEASE_VERSION,
        "git_sha": settings.GIT_SHA,
        "build_timestamp": settings.BUILD_TIMESTAMP,
        "environment": settings.ENVIRONMENT,
    }


# Mount built React SPA in same-origin mode if dist exists
ui_dist_path = os.path.join(os.path.dirname(__file__), "../ui/dist")
if os.path.exists(ui_dist_path):
    app.mount("/", StaticFiles(directory=ui_dist_path, html=True), name="ui")
