import asyncio
from datetime import datetime, timedelta, timezone
import json
import unittest
from unittest.mock import patch

from app.main import app


def call_api(method: str, path: str, body: dict = None) -> tuple[int, dict]:
    """Helper to simulate FastAPI HTTP calls without starting a live server."""
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
                response_headers[k.decode()] = v.decode()
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

    return status_code, data


class TestPhase5ErrorHandling(unittest.TestCase):
    """Integration test suite for Phase 5.6 Production Error Handling."""

    def test_400_business_validation_error(self):
        now = datetime.now(timezone.utc)
        start = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        end = (now - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
        status_code, data = call_api("GET", f"/api/v1/posts?start_date={start}&end_date={end}")
        self.assertEqual(status_code, 400)
        self.assertEqual(data["error"], "bad_request")
        self.assertIn("start_date cannot be after end_date", data["message"])

    def test_404_resource_not_found(self):
        status_code, data = call_api("GET", "/api/v1/posts/999999")
        self.assertEqual(status_code, 404)
        self.assertEqual(data["error"], "not_found")
        self.assertIn("not found", data["message"].lower())

    def test_422_request_validation_error(self):
        status_code, data = call_api("GET", "/api/v1/posts?limit=invalid_number")
        self.assertEqual(status_code, 422)
        self.assertEqual(data["error"], "validation_error")
        self.assertIn("details", data)

    @patch("app.services.analytics.AnalyticsService.get_posts")
    def test_500_unhandled_exception_safety(self, mock_get_posts):
        mock_get_posts.side_effect = RuntimeError("Database connection string postgresql://user:secret_pass@localhost:5432 failed!")

        status_code, data = call_api("GET", "/api/v1/posts")
        self.assertEqual(status_code, 500)
        self.assertEqual(data["error"], "internal_error")

        # Crucial security check: Ensure internal secrets/stack traces are NOT exposed
        raw_response = json.dumps(data)
        self.assertNotIn("secret_pass", raw_response)
        self.assertNotIn("RuntimeError", raw_response)
        self.assertNotIn("Traceback", raw_response)

    def test_legacy_health_endpoint(self):
        status_code, data = call_api("GET", "/health")
        self.assertEqual(status_code, 200)
        self.assertEqual(data, {"status": "ok"})


if __name__ == "__main__":
    unittest.main()
