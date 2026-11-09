"""Application assembly and lifecycle for app."""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from app.routers.appeals import router as appeals_router
from app.routers.health import router as health_router
from app.storage import JsonAppealStore


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Initialize required resources before marking this instance ready.
    app.state.ready = True
    try:
        yield
    finally:
        app.state.ready = False
        # Close application resources here.


def create_app(*, data_dir: str | Path | None = None) -> FastAPI:
    """Build an application with its own configurable appeal store."""
    app = FastAPI(title="Subscriber Appeals API", lifespan=lifespan)
    app.state.ready = False
    app.state.appeal_store = JsonAppealStore(
        Path(data_dir if data_dir is not None else os.getenv("APPEALS_DATA_DIR", "data/appeals"))
    )
    app.include_router(appeals_router)
    app.include_router(health_router)
    return app


app = create_app()
