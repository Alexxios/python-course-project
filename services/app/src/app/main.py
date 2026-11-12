"""Application assembly and lifecycle for app."""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.errors import database_error_handler, validation_error_handler
from app.routers.appeals import router as appeals_router
from app.routers.health import router as health_router
from app.routers.students import router as students_router
from app.storage import JsonAppealStore
from app.students.database import create_database
from app.students.repository import StudentRepository


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Initialize required resources before marking this instance ready.
    app.state.ready = True
    try:
        yield
    finally:
        app.state.ready = False
        app.state.student_engine.dispose()


def create_app(*, data_dir: str | Path | None = None, database_url: str | None = None) -> FastAPI:
    """Build an application with independent appeal storage and student database."""
    app = FastAPI(title="Python Course API", lifespan=lifespan)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(SQLAlchemyError, database_error_handler)
    app.state.ready = False
    app.state.appeal_store = JsonAppealStore(
        Path(data_dir if data_dir is not None else os.getenv("APPEALS_DATA_DIR", "data/appeals"))
    )
    # Engine construction is lazy: schema changes run only via the migration command.
    app.state.student_engine = create_database(database_url)
    app.state.student_repository = StudentRepository(app.state.student_engine)
    app.include_router(appeals_router)
    app.include_router(health_router)
    app.include_router(students_router)
    return app


app = create_app()
