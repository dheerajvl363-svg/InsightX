"""
Phase 5.2 — API Schemas & Validation: test suite.

Covers:
  - HealthResponse schema (construction, validation, serialisation)
  - ServiceStatus schema
  - PaginationParams (valid, boundary, invalid)
  - DateTimeFilter (valid, start-after-end rejection)
  - PlatformFilter (canonical names, aliases, invalid names, deduplication)
  - ErrorDetail / ErrorResponse schemas
  - PagedResponse generic envelope
  - GET /api/v1/health response model enforcement
  - Legacy /health backward-compatibility guard
  - KNOWN_PLATFORMS / PLATFORM_ALIASES constants
"""

import asyncio
import json
import unittest
from datetime import datetime, timezone, timedelta

from pydantic import ValidationError

from app.schemas.common import (
    KNOWN_PLATFORMS,
    PLATFORM_ALIASES,
    DateTimeFilter,
    ErrorDetail,
    ErrorResponse,
    HealthResponse,
    PagedResponse,
    PaginationParams,
    PlatformFilter,
    ServiceStatus,
)
from app.config import APP_ENV, APP_VERSION
from app.main import app


# ---------------------------------------------------------------------------
# ASGI call helper (mirrors project convention)
# ---------------------------------------------------------------------------

def call_api(method: str, path: str, body=None) -> tuple[int, dict]:
    body_bytes = json.dumps(body).encode() if body is not None else b""
    status_code = None
    response_body: list[bytes] = []

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method.upper(),
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body_bytes)).encode()),
        ],
    }

    async def receive():
        return {"type": "http.request", "body": body_bytes, "more_body": False}

    async def send(message):
        nonlocal status_code
        if message["type"] == "http.response.start":
            status_code = message["status"]
        elif message["type"] == "http.response.body":
            response_body.append(message.get("body", b""))

    asyncio.run(app(scope, receive, send))
    raw = b"".join(response_body).decode()
    try:
        data = json.loads(raw)
    except Exception:
        data = {"raw_text": raw}
    return status_code, data


# ===========================================================================
# HealthResponse
# ===========================================================================

class TestHealthResponse(unittest.TestCase):
    """Schema-level tests for HealthResponse."""

    def _make(self, **kwargs) -> HealthResponse:
        defaults = dict(status="ok", version="5.1.0", environment="test", services={})
        defaults.update(kwargs)
        return HealthResponse(**defaults)

    def test_valid_construction(self):
        h = self._make()
        self.assertEqual(h.status, "ok")

    def test_version_stored(self):
        h = self._make(version="1.2.3")
        self.assertEqual(h.version, "1.2.3")

    def test_environment_stored(self):
        h = self._make(environment="production")
        self.assertEqual(h.environment, "production")

    def test_services_stored(self):
        svc = {"analytics_engine": "ok", "ingestion": "ok"}
        h = self._make(services=svc)
        self.assertEqual(h.services["analytics_engine"], "ok")

    def test_services_default_empty_dict(self):
        h = self._make()
        self.assertIsInstance(h.services, dict)

    def test_degraded_status_accepted(self):
        h = self._make(status="degraded")
        self.assertEqual(h.status, "degraded")

    def test_unavailable_status_accepted(self):
        h = self._make(status="unavailable")
        self.assertEqual(h.status, "unavailable")

    def test_invalid_status_rejected(self):
        with self.assertRaises(ValidationError):
            self._make(status="unknown")

    def test_serialises_to_dict(self):
        h = self._make(services={"a": "ok"})
        d = h.model_dump()
        self.assertIn("status", d)
        self.assertIn("version", d)
        self.assertIn("environment", d)
        self.assertIn("services", d)

    def test_version_must_be_string(self):
        with self.assertRaises(ValidationError):
            self._make(version=123)  # type: ignore

    def test_reflects_config_app_version(self):
        h = self._make(version=APP_VERSION)
        self.assertEqual(h.version, APP_VERSION)

    def test_reflects_config_app_env(self):
        h = self._make(environment=APP_ENV)
        self.assertEqual(h.environment, APP_ENV)


# ===========================================================================
# ServiceStatus
# ===========================================================================

class TestServiceStatus(unittest.TestCase):
    """Schema-level tests for ServiceStatus."""

    def test_ok_status(self):
        s = ServiceStatus(name="ingestion", status="ok")
        self.assertEqual(s.status, "ok")

    def test_degraded_status(self):
        s = ServiceStatus(name="ingestion", status="degraded")
        self.assertEqual(s.status, "degraded")

    def test_unavailable_status(self):
        s = ServiceStatus(name="ingestion", status="unavailable")
        self.assertEqual(s.status, "unavailable")

    def test_invalid_status_rejected(self):
        with self.assertRaises(ValidationError):
            ServiceStatus(name="x", status="bad")

    def test_detail_optional(self):
        s = ServiceStatus(name="x", status="ok")
        self.assertIsNone(s.detail)

    def test_detail_stored(self):
        s = ServiceStatus(name="x", status="degraded", detail="latency spike")
        self.assertEqual(s.detail, "latency spike")

    def test_name_stored(self):
        s = ServiceStatus(name="analytics_engine", status="ok")
        self.assertEqual(s.name, "analytics_engine")


# ===========================================================================
# PaginationParams
# ===========================================================================

class TestPaginationParams(unittest.TestCase):
    """PaginationParams: valid, boundary, and invalid values."""

    def test_defaults(self):
        p = PaginationParams()
        self.assertEqual(p.limit, 50)
        self.assertEqual(p.offset, 0)

    def test_custom_limit(self):
        p = PaginationParams(limit=100)
        self.assertEqual(p.limit, 100)

    def test_custom_offset(self):
        p = PaginationParams(offset=200)
        self.assertEqual(p.offset, 200)

    def test_min_limit(self):
        p = PaginationParams(limit=1)
        self.assertEqual(p.limit, 1)

    def test_max_limit(self):
        p = PaginationParams(limit=500)
        self.assertEqual(p.limit, 500)

    def test_limit_zero_rejected(self):
        with self.assertRaises(ValidationError):
            PaginationParams(limit=0)

    def test_limit_above_max_rejected(self):
        with self.assertRaises(ValidationError):
            PaginationParams(limit=501)

    def test_negative_limit_rejected(self):
        with self.assertRaises(ValidationError):
            PaginationParams(limit=-1)

    def test_negative_offset_rejected(self):
        with self.assertRaises(ValidationError):
            PaginationParams(offset=-1)

    def test_zero_offset_valid(self):
        p = PaginationParams(offset=0)
        self.assertEqual(p.offset, 0)

    def test_large_offset_valid(self):
        p = PaginationParams(offset=10000)
        self.assertEqual(p.offset, 10000)


# ===========================================================================
# DateTimeFilter
# ===========================================================================

_NOW = datetime(2026, 9, 9, 0, 0, 0, tzinfo=timezone.utc)
_LATER = _NOW + timedelta(hours=24)
_EARLIER = _NOW - timedelta(hours=24)


class TestDateTimeFilter(unittest.TestCase):
    """DateTimeFilter: valid ranges and cross-field validation."""

    def test_both_none_valid(self):
        f = DateTimeFilter()
        self.assertIsNone(f.start)
        self.assertIsNone(f.end)

    def test_start_only(self):
        f = DateTimeFilter(start=_NOW)
        self.assertEqual(f.start, _NOW)
        self.assertIsNone(f.end)

    def test_end_only(self):
        f = DateTimeFilter(end=_LATER)
        self.assertIsNone(f.start)
        self.assertEqual(f.end, _LATER)

    def test_valid_range(self):
        f = DateTimeFilter(start=_EARLIER, end=_NOW)
        self.assertEqual(f.start, _EARLIER)
        self.assertEqual(f.end, _NOW)

    def test_equal_start_end_valid(self):
        f = DateTimeFilter(start=_NOW, end=_NOW)
        self.assertEqual(f.start, f.end)

    def test_start_after_end_rejected(self):
        with self.assertRaises(ValidationError):
            DateTimeFilter(start=_LATER, end=_NOW)

    def test_start_after_end_error_message(self):
        try:
            DateTimeFilter(start=_LATER, end=_NOW)
            self.fail("Expected ValidationError")
        except ValidationError as exc:
            self.assertIn("start", str(exc))

    def test_serialises_to_dict(self):
        f = DateTimeFilter(start=_NOW, end=_LATER)
        d = f.model_dump()
        self.assertIn("start", d)
        self.assertIn("end", d)


# ===========================================================================
# PlatformFilter
# ===========================================================================

class TestPlatformFilter(unittest.TestCase):
    """PlatformFilter: canonical names, aliases, deduplication, invalid values."""

    def test_none_is_valid(self):
        f = PlatformFilter(platforms=None)
        self.assertIsNone(f.platforms)

    def test_default_is_none(self):
        f = PlatformFilter()
        self.assertIsNone(f.platforms)

    def test_canonical_x(self):
        f = PlatformFilter(platforms=["X"])
        self.assertEqual(f.platforms, ["X"])

    def test_canonical_telegram(self):
        f = PlatformFilter(platforms=["Telegram"])
        self.assertEqual(f.platforms, ["Telegram"])

    def test_canonical_reddit(self):
        f = PlatformFilter(platforms=["Reddit"])
        self.assertEqual(f.platforms, ["Reddit"])

    def test_canonical_youtube(self):
        f = PlatformFilter(platforms=["YouTube"])
        self.assertEqual(f.platforms, ["YouTube"])

    def test_alias_twitter_maps_to_x(self):
        f = PlatformFilter(platforms=["twitter"])
        self.assertEqual(f.platforms, ["X"])

    def test_alias_case_insensitive(self):
        f = PlatformFilter(platforms=["TWITTER"])
        self.assertEqual(f.platforms, ["X"])

    def test_multiple_valid_platforms(self):
        f = PlatformFilter(platforms=["X", "Reddit"])
        self.assertIn("X", f.platforms)
        self.assertIn("Reddit", f.platforms)

    def test_deduplication(self):
        f = PlatformFilter(platforms=["X", "twitter", "X"])
        self.assertEqual(f.platforms.count("X"), 1)

    def test_empty_list_yields_none(self):
        # An empty list after dedup → None (no filter)
        f = PlatformFilter(platforms=[])
        self.assertIsNone(f.platforms)

    def test_invalid_platform_rejected(self):
        with self.assertRaises(ValidationError):
            PlatformFilter(platforms=["Facebook"])

    def test_multiple_invalid_rejected(self):
        with self.assertRaises(ValidationError):
            PlatformFilter(platforms=["Facebook", "TikTok"])

    def test_mixed_valid_invalid_rejected(self):
        with self.assertRaises(ValidationError):
            PlatformFilter(platforms=["X", "Facebook"])

    def test_blank_string_rejected(self):
        with self.assertRaises(ValidationError):
            PlatformFilter(platforms=["   "])

    def test_known_platforms_constant(self):
        self.assertIn("X", KNOWN_PLATFORMS)
        self.assertIn("Telegram", KNOWN_PLATFORMS)
        self.assertIn("Reddit", KNOWN_PLATFORMS)
        self.assertIn("YouTube", KNOWN_PLATFORMS)

    def test_platform_aliases_constant(self):
        self.assertEqual(PLATFORM_ALIASES.get("twitter"), "X")
        self.assertEqual(PLATFORM_ALIASES.get("x"), "X")
        self.assertEqual(PLATFORM_ALIASES.get("telegram"), "Telegram")
        self.assertEqual(PLATFORM_ALIASES.get("reddit"), "Reddit")
        self.assertEqual(PLATFORM_ALIASES.get("youtube"), "YouTube")


# ===========================================================================
# ErrorDetail / ErrorResponse
# ===========================================================================

class TestErrorSchemas(unittest.TestCase):
    """ErrorDetail and ErrorResponse schema construction."""

    def test_error_detail_minimal(self):
        e = ErrorDetail(message="Something went wrong.")
        self.assertEqual(e.message, "Something went wrong.")
        self.assertIsNone(e.field)
        self.assertIsNone(e.code)

    def test_error_detail_full(self):
        e = ErrorDetail(field="platform", message="Invalid value.", code="value_error")
        self.assertEqual(e.field, "platform")
        self.assertEqual(e.code, "value_error")

    def test_error_response_minimal(self):
        r = ErrorResponse(error="not_found", message="Resource not found.")
        self.assertEqual(r.error, "not_found")
        self.assertEqual(r.message, "Resource not found.")
        self.assertEqual(r.details, [])
        self.assertIsNone(r.request_id)

    def test_error_response_with_details(self):
        detail = ErrorDetail(field="limit", message="Must be positive.", code="ge")
        r = ErrorResponse(
            error="validation_error",
            message="Request validation failed.",
            details=[detail],
        )
        self.assertEqual(len(r.details), 1)
        self.assertEqual(r.details[0].field, "limit")

    def test_error_response_with_request_id(self):
        r = ErrorResponse(
            error="server_error",
            message="Unexpected error.",
            request_id="abc-123",
        )
        self.assertEqual(r.request_id, "abc-123")

    def test_error_response_serialises(self):
        r = ErrorResponse(error="e", message="m")
        d = r.model_dump()
        self.assertIn("error", d)
        self.assertIn("message", d)
        self.assertIn("details", d)


# ===========================================================================
# PagedResponse
# ===========================================================================

class TestPagedResponse(unittest.TestCase):
    """PagedResponse generic envelope."""

    def test_empty_items(self):
        r = PagedResponse(total=0, limit=50, offset=0, items=[])
        self.assertEqual(r.total, 0)
        self.assertEqual(r.items, [])

    def test_with_items(self):
        r = PagedResponse(total=3, limit=50, offset=0, items=["a", "b", "c"])
        self.assertEqual(len(r.items), 3)

    def test_pagination_fields(self):
        r = PagedResponse(total=100, limit=20, offset=40, items=[])
        self.assertEqual(r.limit, 20)
        self.assertEqual(r.offset, 40)
        self.assertEqual(r.total, 100)

    def test_negative_total_rejected(self):
        with self.assertRaises(ValidationError):
            PagedResponse(total=-1, limit=10, offset=0, items=[])

    def test_serialises_to_dict(self):
        r = PagedResponse(total=1, limit=50, offset=0, items=[{"id": 1}])
        d = r.model_dump()
        self.assertIn("total", d)
        self.assertIn("items", d)


# ===========================================================================
# API endpoint — GET /api/v1/health (Phase 5.2: typed response model)
# ===========================================================================

class TestVersionedHealthEndpointPhase52(unittest.TestCase):
    """Endpoint tests verifying Phase 5.2 HealthResponse model is enforced."""

    def setUp(self):
        self.code, self.data = call_api("GET", "/api/v1/health")

    def test_returns_200(self):
        self.assertEqual(self.code, 200)

    def test_status_field_is_ok(self):
        self.assertEqual(self.data["status"], "ok")

    def test_version_field_present(self):
        self.assertIn("version", self.data)

    def test_version_matches_config(self):
        self.assertEqual(self.data["version"], APP_VERSION)

    def test_environment_field_present(self):
        self.assertIn("environment", self.data)

    def test_environment_matches_config(self):
        self.assertEqual(self.data["environment"], APP_ENV)

    def test_services_field_is_dict(self):
        self.assertIsInstance(self.data["services"], dict)

    def test_services_analytics_engine_ok(self):
        self.assertEqual(self.data["services"]["analytics_engine"], "ok")

    def test_services_ingestion_ok(self):
        self.assertEqual(self.data["services"]["ingestion"], "ok")

    def test_services_analytics_ok(self):
        self.assertEqual(self.data["services"]["analytics"], "ok")

    def test_response_deserialises_to_health_response(self):
        """The JSON response must be parseable by the HealthResponse schema."""
        parsed = HealthResponse(**self.data)
        self.assertEqual(parsed.status, "ok")

    def test_no_extra_unexpected_fields(self):
        expected_keys = {"status", "version", "environment", "services"}
        self.assertEqual(set(self.data.keys()), expected_keys)


# ===========================================================================
# Legacy /health — backward-compatibility guard
# ===========================================================================

class TestLegacyHealthPhase52Guard(unittest.TestCase):
    """Phase 5.2 must not break the legacy root /health response."""

    def test_returns_200(self):
        code, _ = call_api("GET", "/health")
        self.assertEqual(code, 200)

    def test_exact_response_unchanged(self):
        _, data = call_api("GET", "/health")
        self.assertEqual(data, {"status": "ok"})

    def test_no_version_in_legacy_response(self):
        _, data = call_api("GET", "/health")
        self.assertNotIn("version", data)

    def test_no_environment_in_legacy_response(self):
        _, data = call_api("GET", "/health")
        self.assertNotIn("environment", data)


if __name__ == "__main__":
    unittest.main()
