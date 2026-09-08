"""
Phase 5.6 — Global FastAPI Exception Handlers.

Provides centralized error handling mapping application exceptions, validation errors,
HTTP exceptions, and unexpected failures to standardized, safe ErrorResponse envelopes.
"""

import logging
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.exceptions import InsightXException

logger = logging.getLogger(__name__)


def setup_exception_handlers(app: FastAPI) -> None:
    """Registers global exception handlers on the FastAPI application instance."""

    @app.exception_handler(InsightXException)
    async def insightx_exception_handler(request: Request, exc: InsightXException):
        status_code = status.HTTP_400_BAD_REQUEST
        if exc.error_code == "not_found":
            status_code = status.HTTP_404_NOT_FOUND
        elif exc.error_code == "service_unavailable":
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        elif exc.error_code == "internal_error":
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

        logger.warning(
            "Application exception [%s] at %s: %s",
            exc.error_code,
            request.url.path,
            exc.message,
        )

        return JSONResponse(
            status_code=status_code,
            content={
                "error": exc.error_code,
                "message": exc.message,
                "detail": exc.message,
                "details": exc.details,
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        error_code = "bad_request"
        if exc.status_code == 404:
            error_code = "not_found"
        elif exc.status_code == 422:
            error_code = "validation_error"
        elif exc.status_code >= 500:
            error_code = "internal_error"

        message = str(exc.detail) if exc.detail else "An HTTP error occurred."

        if exc.status_code >= 500:
            logger.error(
                "HTTP %s error at %s: %s",
                exc.status_code,
                request.url.path,
                exc.detail,
                exc_info=True,
            )
        else:
            logger.info("HTTP %s at %s: %s", exc.status_code, request.url.path, exc.detail)

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": error_code,
                "message": message,
                "detail": exc.detail,
                "details": [],
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        field_details = []
        for err in exc.errors():
            field_name = ".".join([str(loc) for loc in err.get("loc", []) if loc != "body"])
            field_details.append(
                {
                    "field": field_name or None,
                    "message": err.get("msg", "Invalid input"),
                    "code": err.get("type", "value_error"),
                }
            )

        logger.info(
            "Request validation error at %s: %s",
            request.url.path,
            exc.errors(),
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "validation_error",
                "message": "Request validation failed.",
                "detail": exc.errors(),
                "details": field_details,
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.error(
            "Unhandled exception at %s: %s",
            request.url.path,
            exc,
            exc_info=True,
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "internal_error",
                "message": "An internal server error occurred.",
                "detail": "An internal server error occurred.",
                "details": [],
                "request_id": getattr(request.state, "request_id", None),
            },
        )
