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


class TestPhase5DataTimelineAPI(unittest.TestCase):
    """Integration test suite for Phase 5.4 Data, Posts & Timeline REST APIs."""

    def test_get_posts_default(self):
        status_code, data = call_api("GET", "/api/v1/posts")
        self.assertEqual(status_code, 200)
        self.assertIn("total", data)
        self.assertIn("limit", data)
        self.assertIn("offset", data)
        self.assertIn("items", data)

    def test_get_posts_pagination(self):
        status_code, data = call_api("GET", "/api/v1/posts?limit=5&offset=0")
        self.assertEqual(status_code, 200)
        self.assertEqual(data["limit"], 5)
        self.assertEqual(data["offset"], 0)

    def test_get_posts_platform_filter(self):
        status_code, data = call_api("GET", "/api/v1/posts?platform=X")
        self.assertEqual(status_code, 200)
        self.assertIn("items", data)

    def test_get_posts_search_filter(self):
        status_code, data = call_api("GET", "/api/v1/posts?search=analytics")
        self.assertEqual(status_code, 200)
        self.assertIn("items", data)

    def test_get_posts_date_filter(self):
        now = datetime.now(timezone.utc)
        start = (now - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
        end = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        status_code, data = call_api("GET", f"/api/v1/posts?start_date={start}&end_date={end}")
        self.assertEqual(status_code, 200)
        self.assertIn("items", data)

    def test_get_posts_invalid_date_range(self):
        now = datetime.now(timezone.utc)
        start = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        end = (now - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
        status_code, data = call_api("GET", f"/api/v1/posts?start_date={start}&end_date={end}")
        self.assertEqual(status_code, 400)

    def test_get_posts_invalid_pagination(self):
        status_code, data = call_api("GET", "/api/v1/posts?limit=0")
        self.assertEqual(status_code, 422)

    def test_get_single_post_nonexistent(self):
        status_code, data = call_api("GET", "/api/v1/posts/999999")
        self.assertEqual(status_code, 404)
        self.assertIn("detail", data)

    def test_get_platforms(self):
        status_code, data = call_api("GET", "/api/v1/platforms")
        self.assertEqual(status_code, 200)
        self.assertIsInstance(data, list)
        if len(data) > 0:
            self.assertIn("id", data[0])
            self.assertIn("name", data[0])

    def test_get_timeline_default(self):
        status_code, data = call_api("GET", "/api/v1/timeline")
        self.assertEqual(status_code, 200)
        self.assertEqual(data["granularity"], "day")
        self.assertIn("total_buckets", data)
        self.assertIn("total_posts", data)
        self.assertIn("buckets", data)

    def test_get_timeline_granularity_hour(self):
        status_code, data = call_api("GET", "/api/v1/timeline?granularity=hour")
        self.assertEqual(status_code, 200)
        self.assertEqual(data["granularity"], "hour")

    def test_get_timeline_granularity_week(self):
        status_code, data = call_api("GET", "/api/v1/timeline?granularity=week")
        self.assertEqual(status_code, 200)
        self.assertEqual(data["granularity"], "week")

    def test_get_timeline_invalid_granularity(self):
        status_code, data = call_api("GET", "/api/v1/timeline?granularity=invalid_bucket")
        self.assertEqual(status_code, 400)


if __name__ == "__main__":
    unittest.main()
