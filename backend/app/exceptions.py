"""
Phase 5.6 — Centralized Application Exception Hierarchy.

Defines custom exception classes for domain, validation, resource, and service errors.
"""

from typing import List, Optional


class InsightXException(Exception):
    """Base exception class for all InsightX application errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "bad_request",
        details: Optional[List[dict]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or []


class ResourceNotFoundException(InsightXException):
    """Raised when a requested database entity or resource does not exist."""

    def __init__(self, message: str = "Resource not found."):
        super().__init__(message=message, error_code="not_found")


class InvalidInputException(InsightXException):
    """Raised when business logic rules or parameters fail validation."""

    def __init__(self, message: str):
        super().__init__(message=message, error_code="bad_request")


class ServiceUnavailableException(InsightXException):
    """Raised when an underlying database connection or analytics subsystem fails."""

    def __init__(self, message: str = "Service temporarily unavailable."):
        super().__init__(message=message, error_code="service_unavailable")


class InternalServerErrorException(InsightXException):
    """Raised when an unrecoverable internal processing failure occurs."""

    def __init__(self, message: str = "An internal server error occurred."):
        super().__init__(message=message, error_code="internal_error")
