"""
Phase 5.8 — OpenAPI & API Documentation Contract Tests.

Validates that the InsightX OpenAPI schema, application metadata, router tags,
endpoint summaries/descriptions, parameter definitions, response models,
error envelopes, UI documentation routes (/docs, /redoc), and legacy /health
contract remain complete, valid, and regression-protected.
"""

import asyncio
import json
import unittest

from app.config import APP_VERSION
from app.main import app


def call_api(method: str, path: str, body: dict = None) -> tuple[int, dict, dict]:
    """Simulates FastAPI HTTP calls via ASGI without external dependencies."""
    if "?" in path:
        clean_path, query_str = path.split("?", 1)
    else:
        clean_path, query_str = path, ""

    body_bytes = json.dumps(body).encode("utf-8") if body is not None else b""
    response_headers = {}
    response_body = []
    status_code = None

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method.upper(),
        "path": clean_path,
        "raw_path": clean_path.encode(),
        "query_string": query_str.encode(),
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
            for k, v in message.get("headers", []):
                response_headers[k.decode().lower()] = v.decode()
        elif message["type"] == "http.response.body":
            response_body.append(message.get("body", b""))

    async def run():
        await app(scope, receive, send)

    asyncio.run(run())

    raw_text = b"".join(response_body).decode("utf-8")
    try:
        data = json.loads(raw_text)
    except Exception:
        data = {"raw_text": raw_text}

    return status_code, data, response_headers


class TestPhase5OpenAPIContract(unittest.TestCase):
    """Automated OpenAPI contract and regression test suite for Phase 5.8."""

    @classmethod
    def setUpClass(cls):
        cls.status, cls.schema, cls.headers = call_api("GET", "/openapi.json")
        assert cls.status == 200, f"Expected 200 from /openapi.json, got {cls.status}"

    def test_1_openapi_json_status_and_structure(self):
        """Verify /openapi.json returns 200 and root OpenAPI structure."""
        self.assertIn("openapi", self.schema)
        self.assertTrue(self.schema["openapi"].startswith("3."))
        self.assertIn("info", self.schema)
        self.assertIn("paths", self.schema)
        self.assertIn("components", self.schema)

    def test_2_application_metadata(self):
        """Verify application title, version, and description metadata."""
        info = self.schema["info"]
        self.assertEqual(info["title"], "InsightX Social Media Analytics API")
        self.assertEqual(info["version"], APP_VERSION)
        self.assertIn("social media intelligence", info["description"].lower())

    def test_3_expected_openapi_tags(self):
        """Verify all declared API tags exist in openapi_tags metadata."""
        tags = {tag["name"] for tag in self.schema.get("tags", [])}
        expected_tags = {
            "Health",
            "Posts",
            "Platforms",
            "Timeline",
            "Analytics",
            "Ingestion",
            "Analytics Engine",
        }
        for tag in expected_tags:
            self.assertIn(tag, tags)

    def test_4_core_endpoints_presence(self):
        """Verify all core Phase 5.1–5.8 endpoints exist in paths."""
        paths = self.schema["paths"]
        expected_paths = [
            "/health",
            "/api/v1/health",
            "/api/v1/posts",
            "/api/v1/posts/{post_id}",
            "/api/v1/platforms",
            "/api/v1/timeline",
            "/api/v1/analytics/sentiment",
            "/api/v1/analytics/topics",
            "/api/v1/analytics/trends",
            "/api/v1/analytics/network",
            "/api/v1/analytics/overview",
            "/api/v1/analytics/platforms/compare",
        ]
        for path in expected_paths:
            self.assertIn(path, paths, f"Missing required path: {path}")

    def test_5_http_methods_and_summaries(self):
        """Verify required HTTP methods, summaries, and descriptions on endpoints."""
        paths = self.schema["paths"]

        # /api/v1/posts (GET)
        self.assertIn("get", paths["/api/v1/posts"])
        get_posts = paths["/api/v1/posts"]["get"]
        self.assertTrue(bool(get_posts.get("summary")))
        self.assertTrue(bool(get_posts.get("description")))
        self.assertIn("Posts", get_posts.get("tags", []))

        # /api/v1/timeline (GET)
        self.assertIn("get", paths["/api/v1/timeline"])
        get_timeline = paths["/api/v1/timeline"]["get"]
        self.assertIn("Timeline", get_timeline.get("tags", []))

        # /api/v1/analytics/sentiment (GET and POST)
        self.assertIn("get", paths["/api/v1/analytics/sentiment"])
        self.assertIn("post", paths["/api/v1/analytics/sentiment"])

        # /api/v1/analytics/overview (GET)
        self.assertIn("get", paths["/api/v1/analytics/overview"])

    def test_6_query_parameters_documented(self):
        """Verify key query parameters are documented for GET /api/v1/posts and GET /api/v1/timeline."""
        posts_params = {
            p["name"]: p for p in self.schema["paths"]["/api/v1/posts"]["get"]["parameters"]
        }
        for param in ["platform", "language", "start_date", "end_date", "search", "sort_by", "limit", "offset"]:
            self.assertIn(param, posts_params, f"Missing query param '{param}' in GET /api/v1/posts")

        timeline_params = {
            p["name"]: p for p in self.schema["paths"]["/api/v1/timeline"]["get"]["parameters"]
        }
        for param in ["platform", "start_date", "end_date", "granularity"]:
            self.assertIn(param, timeline_params, f"Missing query param '{param}' in GET /api/v1/timeline")

    def test_7_response_schemas_and_error_envelope(self):
        """Verify Pydantic schemas and ErrorResponse model exist in components.schemas."""
        schemas = self.schema["components"]["schemas"]
        expected_schemas = [
            "ErrorResponse",
            "ErrorDetail",
            "HealthResponse",
            "PostSummary",
            "PostListResponse",
            "TimelineResponse",
            "DashboardOverviewResponse",
            "PlatformComparisonResponse",
        ]
        for schema_name in expected_schemas:
            self.assertIn(schema_name, schemas, f"Missing schema in OpenAPI components: {schema_name}")

    def test_8_explicit_error_status_code_responses(self):
        """Verify error status codes (400, 422, 500) are documented on GET /api/v1/posts."""
        responses = self.schema["paths"]["/api/v1/posts"]["get"]["responses"]
        self.assertIn("200", responses)
        self.assertIn("400", responses)
        self.assertIn("422", responses)
        self.assertIn("500", responses)

    def test_9_ui_documentation_endpoints(self):
        """Verify FastAPI's native /docs (Swagger) and /redoc (ReDoc) endpoints load cleanly."""
        status_docs, body_docs, headers_docs = call_api("GET", "/docs")
        self.assertEqual(status_docs, 200)
        self.assertIn("text/html", headers_docs.get("content-type", "").lower())
        self.assertIn("swagger", body_docs.get("raw_text", "").lower())

        status_redoc, body_redoc, headers_redoc = call_api("GET", "/redoc")
        self.assertEqual(status_redoc, 200)
        self.assertIn("text/html", headers_redoc.get("content-type", "").lower())
        self.assertIn("redoc", body_redoc.get("raw_text", "").lower())

    def test_10_legacy_health_contract_unmodified(self):
        """Verify legacy GET /health probe returns 200 and exact JSON {"status": "ok"}."""
        status, body, _ = call_api("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(body, {"status": "ok"})


if __name__ == "__main__":
    unittest.main()
