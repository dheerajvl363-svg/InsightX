import asyncio
from datetime import datetime, timezone
import json
import unittest

from app.main import app


def call_api(method: str, path: str, body: dict = None) -> tuple[int, dict]:
    """Helper to simulate FastAPI HTTP calls without starting a live server."""
    body_bytes = json.dumps(body).encode("utf-8") if body is not None else b""
    response_headers = {}
    response_body = []
    status_code = None

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


class TestPhase5AnalyticsEndpoints(unittest.TestCase):
    """Integration test suite for Phase 5.3 Analytics REST endpoints."""

    def test_post_sentiment_analytics(self):
        body = {
            "text": "InsightX analytics platform is performing exceptionally well! #AI #Tech"
        }
        status_code, data = call_api("POST", "/api/v1/analytics/sentiment", body)
        self.assertEqual(status_code, 200)
        self.assertEqual(data["total_analyzed"], 1)
        self.assertIn("results", data)
        self.assertEqual(len(data["results"]), 1)
        self.assertIn(data["results"][0]["label"], ["positive", "neutral", "negative"])

    def test_get_sentiment_analytics(self):
        status_code, data = call_api("GET", "/api/v1/analytics/sentiment")
        self.assertEqual(status_code, 200)
        self.assertIn("total_analyzed", data)
        self.assertIn("results", data)

    def test_post_topic_analytics(self):
        body = {
            "raw_posts": [
                {
                    "platform": "twitter",
                    "external_id": "p1",
                    "text": "Machine learning and artificial intelligence are revolutionizing analytics.",
                    "posted_at": datetime.now(timezone.utc).isoformat(),
                },
                {
                    "platform": "reddit",
                    "external_id": "p2",
                    "text": "Clean energy and electric vehicle battery tech is booming.",
                    "posted_at": datetime.now(timezone.utc).isoformat(),
                },
            ]
        }
        status_code, data = call_api("POST", "/api/v1/analytics/topics", body)
        self.assertEqual(status_code, 200)
        self.assertEqual(data["total_posts_analyzed"], 2)
        self.assertIn("topics", data)

    def test_get_topic_analytics(self):
        status_code, data = call_api("GET", "/api/v1/analytics/topics")
        self.assertEqual(status_code, 200)
        self.assertIn("total", data)
        self.assertIn("items", data)

    def test_post_trend_analytics(self):
        body = {
            "raw_posts": [
                {
                    "platform": "twitter",
                    "external_id": "t1",
                    "text": "#AI models spiking in usage across tech sector.",
                    "posted_at": datetime.now(timezone.utc).isoformat(),
                }
            ]
        }
        status_code, data = call_api("POST", "/api/v1/analytics/trends", body)
        self.assertEqual(status_code, 200)
        self.assertIn("total_topics_evaluated", data)
        self.assertIn("trends", data)

    def test_get_trend_analytics(self):
        status_code, data = call_api("GET", "/api/v1/analytics/trends")
        self.assertEqual(status_code, 200)
        self.assertIn("total_topics_evaluated", data)

    def test_post_network_analytics(self):
        body = {
            "raw_posts": [
                {
                    "platform": "twitter",
                    "external_id": "net1",
                    "text": "Great insights from @tech_guru on https://example.com #AI",
                    "author_username": "alice",
                    "posted_at": datetime.now(timezone.utc).isoformat(),
                },
                {
                    "platform": "twitter",
                    "external_id": "net2",
                    "text": "Replying to @alice and @tech_guru with more links https://example.com #AI",
                    "author_username": "bob",
                    "posted_at": datetime.now(timezone.utc).isoformat(),
                },
            ]
        }
        status_code, data = call_api("POST", "/api/v1/analytics/network", body)
        self.assertEqual(status_code, 200)
        self.assertGreater(data["total_nodes"], 0)
        self.assertGreater(data["total_edges"], 0)
        self.assertIn("nodes", data)
        self.assertIn("edges", data)
        self.assertIn("top_influencers", data)
        self.assertIn("top_domains", data)

    def test_get_network_analytics(self):
        status_code, data = call_api("GET", "/api/v1/analytics/network")
        self.assertEqual(status_code, 200)
        self.assertIn("total_nodes", data)
        self.assertIn("total_edges", data)

    def test_empty_post_list_returns_400(self):
        body = {"raw_posts": []}
        status_code, data = call_api("POST", "/api/v1/analytics/sentiment", body)
        self.assertEqual(status_code, 400)


if __name__ == "__main__":
    unittest.main()
