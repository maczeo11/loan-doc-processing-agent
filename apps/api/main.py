"""
FinScan AI: FastAPI Application Entrypoint.

Serves REST API and mounts React SPA from apps/ui/dist.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from apps.api.routes.applications import router as applications_router
from apps.api.routes.documents import router as documents_router
from apps.api.routes.review import router as review_router

app = FastAPI(
    title="FinScan AI API",
    version="1.0.0",
    description="Deterministic code decides. AI explains. A human approves."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register route modules
app.include_router(applications_router)
app.include_router(documents_router)
app.include_router(review_router)


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "ok",
        "service": "finscan-api",
        "version": "1.0.0",
    }


# Mount built React SPA in same-origin mode if dist exists
ui_dist_path = os.path.join(os.path.dirname(__file__), "../ui/dist")
if os.path.exists(ui_dist_path):
    app.mount("/", StaticFiles(directory=ui_dist_path, html=True), name="ui")
