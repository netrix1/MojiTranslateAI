from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.core.logging_config import setup_logging, logger

# Initialize logging immediately
setup_logging()

from app.api.routes_health import router as health_router
from app.api.routes_jobs import router as jobs_router
from app.api.routes_pages import router as pages_router
from app.api.routes_pipeline import router as pipeline_router
from app.api.routes_preview import router as preview_router

app = FastAPI(
    title="MojiTranslateAI API",
    version="0.2.0",
    openapi_version="3.1.0",
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global Exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "error": str(exc)},
    )

from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rotas de API
app.include_router(health_router, tags=["health"])
app.include_router(jobs_router, tags=["jobs"])
app.include_router(pages_router, tags=["pages"])
app.include_router(pipeline_router, tags=["pipeline"])
app.include_router(preview_router, tags=["preview"])

# Frontend estático (regions_viewer.html etc.)
frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount(
        "/frontend",
        StaticFiles(directory=str(frontend_dir), html=True),
        name="frontend",
    )
