"""Render validation failures even when the rejected input is not JSON-safe."""

import json

from fastapi import Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError


async def database_error_handler(_request: Request, _exc: SQLAlchemyError) -> Response:
    return JSONResponse(
        status_code=503,
        content={
            "detail": "The student database is unavailable; check configuration and migrations"
        },
    )


async def validation_error_handler(_request: Request, exc: RequestValidationError) -> Response:
    # Raw input can contain NaN or unpaired surrogates accepted by Python's JSON
    # parser. Keep field diagnostics, without copying unsafe input or context.
    details = [{key: error[key] for key in ("loc", "msg", "type")} for error in exc.errors()]
    return Response(
        content=json.dumps({"detail": details}, ensure_ascii=True, allow_nan=False),
        status_code=422,
        media_type="application/json",
    )
