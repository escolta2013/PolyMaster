from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import logger
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info(f"Starting {settings.PROJECT_NAME} in {'DEBUG' if settings.DEBUG else 'PRODUCTION'} mode")
    yield
    # Shutdown logic
    logger.info(f"Shutting down {settings.PROJECT_NAME}")

from app.engines.tracker import router as tracker_router
from app.engines.wallet import router as wallet_router
from app.engines.ghost import router as ghost_router
from app.engines.autonomous import router as autonomous_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tracker_router.router)
app.include_router(wallet_router.router)
app.include_router(ghost_router.router)
app.include_router(autonomous_router.router)

from app.engines.council.router import router as council_router
app.include_router(council_router)

@app.get("/")
async def health_check():
    return {
        "status": "operational",
        "system": settings.PROJECT_NAME,
        "version": "2.0.0",
        "modules": {
            "tracker": "active",
            "ghost": "standby",
            "council": "standby",
            "flash": "standby"
        }
    }
