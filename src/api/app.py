"""FastAPI application factory.

Creates and configures the FastAPI app instance, registers routers,
adds CORS middleware (localhost only), mounts the frontend/ static files,
and provides a lifespan context for future Playwright / DB startup.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.api.routes.chat import router as chat_router
from src.api.routes.health import router as health_router

_FRONTEND_DIR = Path(__file__).parents[2] / "frontend"


@asynccontextmanager
async def _lifespan(app: FastAPI):
    from src.persistence.database import init_db
    init_db()
    yield
    # Step 10+: shut down Playwright ERPClient.


def create_app() -> FastAPI:
    app = FastAPI(title="Jarvis V2", version="2.0", lifespan=_lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ],
        allow_methods=["GET", "POST", "DELETE", "PATCH"],
        allow_headers=["*"],
    )

    app.include_router(health_router, prefix="/api")
    app.include_router(chat_router, prefix="/api")

    # Serve React/HTML frontend as static files.  Must be mounted last so
    # /api/* routes always take precedence.
    if _FRONTEND_DIR.exists():
        app.mount(
            "/",
            StaticFiles(directory=str(_FRONTEND_DIR), html=True),
            name="frontend",
        )

    return app


# Module-level app instance used by uvicorn: "src.api.app:app"
app = create_app()
