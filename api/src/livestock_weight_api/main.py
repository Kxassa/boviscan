from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db.sqlite import get_connection, init_db
from .routers import events, sessions, status, sync
from .settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = get_connection(settings.db_path)
    init_db(conn)
    app.state.db = conn
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


@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "service": "boviscan-api",
        "product": "BoviScan",
        "project_hint": "boviscan-c2430",
    }


def run() -> None:
    import uvicorn

    uvicorn.run("livestock_weight_api.main:app", host="0.0.0.0", port=8000, reload=False)
