from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.core.config import settings
from app.core.logging import logger
from contextlib import asynccontextmanager
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.PROJECT_NAME} in {'DEBUG' if settings.DEBUG else 'PRODUCTION'} mode")
    logger.info(f"Trading mode: {'SIMULATION' if settings.COPY_SIMULATION else '🔴 REAL MONEY'}")
    yield
    logger.info(f"Shutting down {settings.PROJECT_NAME}")

from app.engines.tracker import router as tracker_router
from app.engines.wallet import router as wallet_router
from app.engines.ghost import router as ghost_router
from app.engines.autonomous import router as autonomous_router
from app.engines.council.router import router as council_router
from app.api.status_router import router as status_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    # In production you can restrict this to the EC2 IP, but for a personal
    # single-user setup, wildcard is fine since port 8000 is not public.
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Core engine routers ──
app.include_router(tracker_router.router)
app.include_router(wallet_router.router)
app.include_router(ghost_router.router)
app.include_router(autonomous_router.router)
app.include_router(council_router)

# ── Dashboard API ──
app.include_router(status_router)

# ── Static files (dashboard.html) ──
_static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_static_dir):
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")

@app.get("/dashboard", include_in_schema=False)
async def dashboard():
    """Serve the terminal dashboard UI (DOS phosphor green style)."""
    path = os.path.join(_static_dir, "dashboard.html")
    return FileResponse(path)

@app.get("/")
async def health_check():
    return {
        "status": "operational",
        "system": settings.PROJECT_NAME,
        "version": "2.0.0",
        "dashboard": "/dashboard",
        "modules": {
            "tracker": "active",
            "ghost": "standby",
            "council": "active",
            "autonomous": "active",
        }
    }
