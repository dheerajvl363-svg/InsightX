"""
Phase 5.1 — FastAPI API Foundation: test suite.

Covers:
  - GET /api/v1/health      (versioned health — Phase 5.1 new endpoint)
  - GET /health             (legacy root health — must stay backward-compatible)
  - GET /db-health          (legacy DB health — must stay backward-compatible)
  - Application metadata    (title, version, lifespan wiring)
"""
import asyncio
import json
import unittest

from app.main import app
from app.config import APP_ENV, APP_VERSION


# ---------------------------------------------------------------------------
# Minimal raw-ASGI call helper (mirrors test_api.py convention)
# ---------------------------------------------------------------------------

def call_api(method: str, path: str, body: dict = None) -> tuple[int, dict]:
    """Execute a raw ASGI HTTP request against the FastAPI application."""
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


# ---------------------------------------------------------------------------
# Phase 5.1: Versioned health endpoint
# ---------------------------------------------------------------------------

class TestVersionedHealthEndpoint(unittest.TestCase):
    """Tests for GET /api/v1/health (Phase 5.1 new endpoint)."""

    def test_versioned_health_returns_200(self):
        code, _ = call_api("GET", "/api/v1/health")
        self.assertEqual(code, 200)

    def test_versioned_health_status_is_ok(self):
        _, data = call_api("GET", "/api/v1/health")
        self.assertEqual(data["status"], "ok")

    def test_versioned_health_has_version(self):
        _, data = call_api("GET", "/api/v1/health")
        self.assertIn("version", data)
        self.assertIsInstance(data["version"], str)
        self.assertTrue(len(data["version"]) > 0)

    def test_versioned_health_version_matches_config(self):
        _, data = call_api("GET", "/api/v1/health")
        self.assertEqual(data["version"], APP_VERSION)

    def test_versioned_health_has_environment(self):
        _, data = call_api("GET", "/api/v1/health")
        self.assertIn("environment", data)
        self.assertIsInstance(data["environment"], str)

    def test_versioned_health_environment_matches_config(self):
        _, data = call_api("GET", "/api/v1/health")
        self.assertEqual(data["environment"], APP_ENV)

    def test_versioned_health_has_services(self):
        _, data = call_api("GET", "/api/v1/health")
        self.assertIn("services", data)
        self.assertIsInstance(data["services"], dict)

    def test_versioned_health_services_analytics_engine_ok(self):
        _, data = call_api("GET", "/api/v1/health")
        self.assertEqual(data["services"].get("analytics_engine"), "ok")

    def test_versioned_health_services_ingestion_ok(self):
        _, data = call_api("GET", "/api/v1/health")
        self.assertEqual(data["services"].get("ingestion"), "ok")

    def test_versioned_health_services_analytics_ok(self):
        _, data = call_api("GET", "/api/v1/health")
        self.assertEqual(data["services"].get("analytics"), "ok")


# ---------------------------------------------------------------------------
# Phase 5.1: Legacy endpoints — backward-compatibility guard
# ---------------------------------------------------------------------------

class TestLegacyHealthBackwardCompatibility(unittest.TestCase):
    """
    Ensures the legacy /health and /db-health endpoints remain exactly as
    they were before Phase 5.1.  Any regression here breaks existing clients.
    """

    def test_root_health_returns_200(self):
        code, _ = call_api("GET", "/health")
        self.assertEqual(code, 200)

    def test_root_health_exact_response(self):
        """Must stay exactly {"status": "ok"} — no extra fields."""
        _, data = call_api("GET", "/health")
        self.assertEqual(data, {"status": "ok"})

    def test_db_health_returns_200(self):
        code, _ = call_api("GET", "/db-health")
        self.assertEqual(code, 200)

    def test_db_health_has_database_key(self):
        _, data = call_api("GET", "/db-health")
        self.assertIn("database", data)

    def test_db_health_database_value_is_string(self):
        _, data = call_api("GET", "/db-health")
        self.assertIsInstance(data["database"], str)


# ---------------------------------------------------------------------------
# Phase 5.1: Application metadata
# ---------------------------------------------------------------------------

class TestApplicationMetadata(unittest.TestCase):
    """Validates that app metadata is correctly propagated from config."""

    def test_app_title(self):
        self.assertEqual(app.title, "InsightX API")

    def test_app_version_matches_config(self):
        self.assertEqual(app.version, APP_VERSION)

    def test_app_has_lifespan(self):
        """Lifespan must be wired (router_lifespan_handler set)."""
        self.assertIsNotNone(app.router.lifespan_context)

    def test_app_openapi_schema_has_version(self):
        schema = app.openapi()
        self.assertIn("info", schema)
        self.assertEqual(schema["info"]["version"], APP_VERSION)

    def test_app_openapi_schema_has_title(self):
        schema = app.openapi()
        self.assertEqual(schema["info"]["title"], "InsightX API")


# ---------------------------------------------------------------------------
# Phase 5.1: Config module
# ---------------------------------------------------------------------------

class TestConfigSettings(unittest.TestCase):
    """Validates that the Phase 5.1 config settings have the expected types."""

    def test_app_env_is_string(self):
        self.assertIsInstance(APP_ENV, str)

    def test_app_version_is_string(self):
        self.assertIsInstance(APP_VERSION, str)

    def test_app_version_not_empty(self):
        self.assertTrue(len(APP_VERSION) > 0)

    def test_app_env_not_empty(self):
        self.assertTrue(len(APP_ENV) > 0)

    def test_debug_imported(self):
        from app.config import DEBUG  # noqa: F401 — just verifying importability
        self.assertIsInstance(DEBUG, bool)


if __name__ == "__main__":
    unittest.main()
