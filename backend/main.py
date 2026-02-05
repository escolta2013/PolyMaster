from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="PolyMaster Engine",
    description="Institutional-grade Algorithmic Trading Core for Polymarket",
    version="1.0.0"
)

# CORS (Allow Frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.engines.tracker.router import router as tracker_router

app.include_router(tracker_router)

@app.get("/")
def health_check():
    return {
        "status": "operational",
        "system": "PolyMaster Core",
        "modules": {
            "tracker": "active",
            "ghost": "standby",
            "council": "standby",
            "flash": "standby"
        }
    }
