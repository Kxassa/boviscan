from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db.sqlite import get_connection, init_db
from .routers import auth_status, bridge, devices, events, reports, sessions, status, sync
from .routers.devices import register_mock_local_device
from .settings import settings


def _mock_auto_register() -> bool:
    """Register local mock device on API start (default on for demo-friendly mode)."""
    v = os.environ.get("LW_MOCK_REGISTER_DEVICE", "true").lower()
    return v in ("1", "true", "yes", "on")


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = get_connection(settings.db_path)
    init_db(conn)
    app.state.db = conn
    if _mock_auto_register():
        register_mock_local_device(conn)
    yield
    conn.close()


app = FastAPI(
    title="BoviScan API",
    version="0.1.0",
    description="Local companion API (SQLite) with Firestore sync for BoviScan weighing sessions",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(events.router)
app.include_router(status.router)
app.include_router(sessions.router)
app.include_router(sync.router)
app.include_router(auth_status.router)
app.include_router(reports.router)
app.include_router(devices.router)
app.include_router(bridge.router)


@app.get("/health")
def health() -> dict:
    from .auth import auth_status
    from .firestore_sync import sync_mode

    return {
        "ok": True,
        "service": "boviscan-api",
        "product": "BoviScan",
        "project_hint": "boviscan-c2430",
        "auth_enabled": auth_status()["enabled"],
        "sync_mode": sync_mode(),
    }


def run() -> None:
    import uvicorn

    uvicorn.run("livestock_weight_api.main:app", host="0.0.0.0", port=8000, reload=False)
