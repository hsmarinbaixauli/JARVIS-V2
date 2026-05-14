from __future__ import annotations

import asyncio
import sys
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

"""FastAPI application factory.

Creates and configures the FastAPI app instance, registers routers,
adds CORS middleware (localhost only), mounts the frontend/ static files,
and provides a lifespan context for future Playwright / DB startup.
"""

import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

_access_log = logging.getLogger("jarvis.access")

from src.api.routes.chat import router as chat_router
from src.api.routes.erp import router as erp_router
from src.api.routes.gmail import router as gmail_router
from src.api.routes.health import router as health_router
from src.api.routes.outlook import router as outlook_router

_FRONTEND_DIR = Path(__file__).parents[2] / "frontend"


@asynccontextmanager
async def _lifespan(app: FastAPI):
    import logging
    import os

    from src.persistence.database import init_db
    init_db()

    # Start the ERP Playwright client when credentials are present.
    if os.getenv("ERP_USER"):
        try:
            from src.api.dependencies import get_services
            from src.erp.client import init_erp_client
            erp = await init_erp_client()
            get_services()["erp"] = erp
            logging.getLogger(__name__).info("ERP client started successfully.")
        except Exception as exc:
            logging.getLogger(__name__).warning(
                "ERP client failed to start (ERP features disabled): %s", exc
            )

    yield

    from src.erp.client import shutdown_erp_client
    await shutdown_erp_client()


def create_app() -> FastAPI:
    app = FastAPI(title="Jarvis V2", version="2.0", lifespan=_lifespan)

    @app.middleware("http")
    async def _log_requests(request: Request, call_next):
        start = time.monotonic()
        response = await call_next(request)
        elapsed_ms = (time.monotonic() - start) * 1000
        _access_log.info(
            "%s %s → %d  (%.0fms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response

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
    app.include_router(gmail_router, prefix="/api")
    app.include_router(outlook_router, prefix="/api")
    app.include_router(erp_router, prefix="/api")

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
