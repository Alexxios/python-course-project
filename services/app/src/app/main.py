"""Application assembly and lifecycle for app."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.config import Settings
from app.database import create_database
from app.errors import conflict_handler, database_error_handler, validation_error_handler
from app.routers.health import router as health_router
from app.routers.v1 import router as v1_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Initialize required resources before marking this instance ready.
    app.state.ready = True
    try:
        yield
    finally:
        app.state.ready = False
        await app.state.engine.dispose()


def create_app(*, settings: Settings | None = None) -> FastAPI:
    """Build an independent API instance; migrate explicitly before starting it."""
    settings = settings if settings is not None else Settings()
    app = FastAPI(
        title="Учебная платформа",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/v1/docs",
        redoc_url="/v1/redoc",
        openapi_url="/v1/openapi.json",
        description="Courses, sequential lessons, automatic grading, progress, and personalized practice.",
    )
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(IntegrityError, conflict_handler)
    app.add_exception_handler(SQLAlchemyError, database_error_handler)
    app.state.ready = False
    app.state.settings = settings
    app.state.engine = create_database(settings.database_url)
    app.state.sessions = async_sessionmaker(app.state.engine, expire_on_commit=False)
    app.include_router(v1_router)
    app.include_router(health_router)
    return app


app = create_app()
