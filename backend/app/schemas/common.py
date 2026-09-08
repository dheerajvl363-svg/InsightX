"""
Phase 5.2 — Common / foundational API schemas.

This module provides reusable Pydantic building blocks used across every
Phase 5 endpoint.  Nothing here contains business logic; these are pure
data-contract types.

Design principles
-----------------
- Follow the existing project convention: ``BaseModel`` + ``Field`` +
  ``ConfigDict(from_attributes=True)``.
- No circular imports: this module must not import from other app.schemas.*
  files (those may import from here).
- Keep every schema focused and minimal — add fields only when an actual
  endpoint needs them.
"""

from datetime import datetime
from typing import Any, Dict, Generic, List, Literal, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Health / Readiness
# ---------------------------------------------------------------------------

# Canonical set of platforms registered in the database (Phase 2 seed).
KNOWN_PLATFORMS: frozenset[str] = frozenset({"X", "Telegram", "Reddit", "YouTube"})

# Valid platform aliases accepted in filter inputs (case-insensitive).
# Maps lowercase alias → canonical name.
PLATFORM_ALIASES: Dict[str, str] = {
    "x": "X",
    "twitter": "X",
    "telegram": "Telegram",
    "reddit": "Reddit",
    "youtube": "YouTube",
}


class ServiceStatus(BaseModel):
    """Readiness status for a single named subsystem."""

    name: str = Field(..., description="Subsystem identifier")
    status: Literal["ok", "degraded", "unavailable"] = Field(
        ..., description="Current readiness state"
    )
    detail: Optional[str] = Field(
        default=None, description="Optional human-readable detail or error message"
    )

    model_config = ConfigDict(from_attributes=True)


class HealthResponse(BaseModel):
    """
    Structured response for ``GET /api/v1/health``.

    Provides richer operational metadata compared to the legacy root
    ``/health`` probe (which returns only ``{"status": "ok"}``).
    """

    status: Literal["ok", "degraded", "unavailable"] = Field(
        ..., description="Overall API readiness status"
    )
    version: str = Field(..., description="Running application version")
    environment: str = Field(..., description="Deployment environment name")
    services: Dict[str, str] = Field(
        default_factory=dict,
        description="Per-subsystem readiness map (subsystem → status string)",
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "status": "ok",
                "version": "1.0.0",
                "environment": "production",
                "services": {
                    "analytics_engine": "ok",
                    "ingestion": "ok",
                    "analytics": "ok",
                },
            }
        },
    )


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

_DEFAULT_LIMIT = 50
_MAX_LIMIT = 500


class PaginationParams(BaseModel):
    """
    Reusable pagination query parameters.

    Attach to any list/search endpoint as a request body fragment or
    query-param model.
    """

    limit: int = Field(
        default=_DEFAULT_LIMIT,
        ge=1,
        le=_MAX_LIMIT,
        description=f"Maximum records to return (1–{_MAX_LIMIT}). Default {_DEFAULT_LIMIT}.",
    )
    offset: int = Field(
        default=0, ge=0, description="Zero-based index of the first record to return."
    )

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Date / Time filters
# ---------------------------------------------------------------------------


class DateTimeFilter(BaseModel):
    """
    Optional inclusive date-range filter.

    Both fields are optional; when both are provided ``start`` must not be
    after ``end``.
    """

    start: Optional[datetime] = Field(
        default=None,
        description="Inclusive lower bound (UTC).  Posts *at or after* this time.",
    )
    end: Optional[datetime] = Field(
        default=None,
        description="Inclusive upper bound (UTC).  Posts *at or before* this time.",
    )

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def start_before_end(self) -> "DateTimeFilter":
        if self.start is not None and self.end is not None:
            if self.start > self.end:
                raise ValueError(
                    f"start ({self.start.isoformat()}) must not be after "
                    f"end ({self.end.isoformat()})."
                )
        return self


# ---------------------------------------------------------------------------
# Platform filter
# ---------------------------------------------------------------------------


class PlatformFilter(BaseModel):
    """
    Optional platform whitelist filter.

    Accepts canonical platform names (X, Telegram, Reddit, YouTube) or
    common aliases (twitter → X).  Invalid names are rejected at
    validation time.
    """

    platforms: Optional[List[str]] = Field(
        default=None,
        description=(
            "Whitelist of platforms to include.  Valid values: "
            + ", ".join(sorted(KNOWN_PLATFORMS))
            + ".  Aliases accepted: twitter → X."
        ),
    )

    model_config = ConfigDict(from_attributes=True)

    @field_validator("platforms", mode="before")
    @classmethod
    def normalise_and_validate_platforms(
        cls, v: Optional[List[str]]
    ) -> Optional[List[str]]:
        if v is None:
            return None
        if not isinstance(v, list):
            raise ValueError("platforms must be a list of strings.")
        normalised: List[str] = []
        invalid: List[str] = []
        for raw in v:
            if not isinstance(raw, str) or not raw.strip():
                invalid.append(repr(raw))
                continue
            canonical = PLATFORM_ALIASES.get(raw.strip().lower())
            if canonical:
                normalised.append(canonical)
            else:
                invalid.append(raw)
        if invalid:
            raise ValueError(
                f"Unknown or unsupported platform value(s): {invalid}. "
                f"Valid platforms: {sorted(KNOWN_PLATFORMS)}."
            )
        # Deduplicate while preserving order
        seen: set[str] = set()
        deduped: List[str] = []
        for p in normalised:
            if p not in seen:
                seen.add(p)
                deduped.append(p)
        return deduped if deduped else None


# ---------------------------------------------------------------------------
# Structured error payloads
# ---------------------------------------------------------------------------


class ErrorDetail(BaseModel):
    """Single field-level validation error detail."""

    field: Optional[str] = Field(
        default=None,
        description="Dot-separated field path that caused the error, if applicable.",
    )
    message: str = Field(..., description="Human-readable error description.")
    code: Optional[str] = Field(
        default=None,
        description="Machine-readable error code (e.g. 'value_error', 'missing').",
    )

    model_config = ConfigDict(from_attributes=True)


class ErrorResponse(BaseModel):
    """
    Standard JSON error envelope returned by all Phase 5 endpoints on
    4xx / 5xx responses.

    FastAPI's default 422 Unprocessable Entity body is not replaced by
    this schema — this is used for deliberate application-level errors
    (HTTPException details) documented in the OpenAPI spec.
    """

    error: str = Field(..., description="Short error category (e.g. 'not_found').")
    message: str = Field(..., description="Human-readable explanation of the error.")
    details: List[ErrorDetail] = Field(
        default_factory=list,
        description="Optional list of per-field validation error details.",
    )
    request_id: Optional[str] = Field(
        default=None,
        description="Correlation ID for tracing, if available.",
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "error": "bad_request",
                "message": "start_date cannot be after end_date.",
                "details": [
                    {
                        "field": "start_date",
                        "message": "start_date (2026-09-10) must be <= end_date (2026-09-01)",
                        "code": "value_error",
                    }
                ],
                "request_id": "req-8f92a10",
            }
        },
    )


# ---------------------------------------------------------------------------
# Generic paged response envelope
# ---------------------------------------------------------------------------

ItemT = TypeVar("ItemT")


class PagedResponse(BaseModel, Generic[ItemT]):
    """
    Generic paginated list envelope.

    Usage example::

        response_model=PagedResponse[PostSummary]

    Fields
    ------
    total   : Total records matching the query (before pagination).
    limit   : Page size used.
    offset  : Offset used.
    items   : Records for this page.
    """

    total: int = Field(..., ge=0, description="Total matching records (pre-pagination).")
    limit: int = Field(..., ge=1, description="Page size applied.")
    offset: int = Field(..., ge=0, description="Offset applied.")
    items: List[Any] = Field(default_factory=list, description="Records for this page.")

    model_config = ConfigDict(from_attributes=True)
