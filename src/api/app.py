"""FastAPI application factory. Creates and configures the FastAPI app instance,
registers routers, adds CORS middleware (localhost only), mounts frontend static
files, and wires up the lifespan context for startup/shutdown of Playwright and
other services."""
from __future__ import annotations


def create_app():
    pass
