import asyncio
from datetime import datetime, timedelta, timezone
import json
import unittest

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


class TestPhase5CombinedAnalyticsAPI(unittest.TestCase):
    """Integration test suite for Phase 5.5 Combined / Dashboard Analytics APIs."""

    def test_get_overview_default(self):
        status_code, data = call_api("GET", "/api/v1/analytics/overview")
        self.assertEqual(status_code, 200)
        self.assertIn("total_posts", data)
        self.assertIn("engagement_summary", data)
        self.assertIn("platforms", data)
        self.assertIn("generated_at", data)

    def test_get_overview_platform_filter(self):
        status_code, data = call_api("GET", "/api/v1/analytics/overview?platform=X")
        self.assertEqual(status_code, 200)
        self.assertIn("total_posts", data)

    def test_get_overview_date_filter(self):
        now = datetime.now(timezone.utc)
        start = (now - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
        end = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        status_code, data = call_api("GET", f"/api/v1/analytics/overview?start_date={start}&end_date={end}")
        self.assertEqual(status_code, 200)

    def test_get_overview_invalid_date_range(self):
        now = datetime.now(timezone.utc)
        start = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        end = (now - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
        status_code, data = call_api("GET", f"/api/v1/analytics/overview?start_date={start}&end_date={end}")
        self.assertEqual(status_code, 400)

    def test_get_platform_comparison(self):
        status_code, data = call_api("GET", "/api/v1/analytics/platforms/compare")
        self.assertEqual(status_code, 200)
        self.assertIn("total_platforms", data)
        self.assertIn("platforms", data)
        self.assertIn("generated_at", data)

    def test_get_platform_comparison_date_filter(self):
        now = datetime.now(timezone.utc)
        start = (now - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
        end = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        status_code, data = call_api("GET", f"/api/v1/analytics/platforms/compare?start_date={start}&end_date={end}")
        self.assertEqual(status_code, 200)


if __name__ == "__main__":
    unittest.main()
