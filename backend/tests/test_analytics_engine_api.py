import asyncio
from datetime import datetime, timezone
import json
import unittest
from unittest.mock import patch

from app.main import app


def call_api(method: str, path: str, body: dict = None) -> tuple[int, dict]:
    """
    Executes a native ASGI HTTP request against the FastAPI application.
    Tests full FastAPI pipeline: routing, dependency injection, validation, and serialization.
    """
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


class TestAnalyticsEngineAPI(unittest.TestCase):
    """
    Integration tests for Phase 4.7 Analytics Engine API Layer.
    Verifies routing, request validation, specialized endpoints, filtering, error handling, and capabilities.
    """

    def setUp(self):
        self.sample_posts = [
            {
                "id": "p1",
                "external_id": "ext_p1",
                "platform": "twitter",
                "text": "Artificial Intelligence is completely transforming cloud technology! #AI #Tech",
                "posted_at": "2026-09-08T10:00:00Z",
                "metrics": {"likes": 120, "comments": 30, "shares": 15, "views": 1200},
                "topics": ["AI", "Tech"],
            },
            {
                "id": "p2",
                "external_id": "ext_p2",
                "platform": "twitter",
                "text": "AI models are accelerating software engineering productivity rapidly. #AI",
                "posted_at": "2026-09-08T11:00:00Z",
                "metrics": {"likes": 200, "comments": 50, "shares": 40, "views": 2500},
                "topics": ["AI"],
            },
            {
                "id": "p3",
                "external_id": "ext_p3",
                "platform": "reddit",
                "text": "Climate change and renewable solar energy adoption reached new records. #Climate",
                "posted_at": "2026-09-08T12:00:00Z",
                "metrics": {"likes": 80, "comments": 20, "shares": 5, "views": 900},
                "topics": ["Climate"],
            },
            {
                "id": "p4",
                "external_id": "ext_p4",
                "platform": "reddit",
                "text": "Terrible system crash and outage disrupted our entire production today. #DevOps",
                "posted_at": "2026-09-08T13:00:00Z",
                "metrics": {"likes": 40, "comments": 15, "shares": 2, "views": 400},
                "topics": ["DevOps"],
            },
        ]

    def test_1_health_and_capabilities_endpoints(self):
        """Test GET /api/v1/analytics/engine/health and /capabilities."""
        code, data = call_api("GET", "/api/v1/analytics/engine/health")
        self.assertEqual(code, 200)
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["service"], "analytics_engine")

        code, cap = call_api("GET", "/api/v1/analytics/engine/capabilities")
        self.assertEqual(code, 200)
        self.assertEqual(cap["status"], "ok")
        self.assertEqual(cap["api_version"], "1.0.0")
        self.assertIn("hour", cap["supported_intervals"])
        self.assertIn("day", cap["supported_intervals"])
        self.assertIn("week", cap["supported_intervals"])
        self.assertIn("engagement_analytics", cap["supported_capabilities"])
        self.assertIn("narrative_intelligence", cap["supported_capabilities"])
        self.assertIn("advanced_time_series", cap["supported_capabilities"])
        self.assertEqual(cap["engines"]["engagement"], "EngagementEngine")

    def test_2_analyze_comprehensive_endpoint_with_posts(self):
        """Test POST /api/v1/analytics/engine/analyze with pre-structured posts."""
        payload = {
            "posts": self.sample_posts,
            "interval_unit": "hour",
            "rolling_window_size": 2,
            "anomaly_threshold_z": 2.0,
            "top_k": 5,
        }
        code, data = call_api("POST", "/api/v1/analytics/engine/analyze", payload)
        self.assertEqual(code, 200)
        self.assertEqual(data["total_posts_evaluated"], 4)
        self.assertIsNotNone(data["analyzed_at"])
        self.assertIsNotNone(data["engagement_analytics"])
        self.assertGreater(data["engagement_analytics"]["weighted_engagement_score"], 0)
        self.assertIsNotNone(data["temporal_dynamics"])
        self.assertGreaterEqual(len(data["temporal_dynamics"]["buckets"]), 1)
        self.assertIsNotNone(data["detailed_engagement"])
        self.assertIsNotNone(data["detailed_sentiment"])
        self.assertIsNotNone(data["detailed_trends"])
        self.assertIsNotNone(data["detailed_narratives"])
        self.assertIsInstance(data["summary_insights"], list)
        self.assertGreater(len(data["summary_insights"]), 0)

    def test_3_analyze_with_raw_posts_and_normalization(self):
        """Test POST /api/v1/analytics/engine/analyze with raw_posts triggering normalizer/quality pipeline."""
        payload = {
            "raw_posts": [
                {
                    "platform": "twitter",
                    "external_id": "raw_1",
                    "text": "Exploring quantum computing breakthroughs in 2026. #Quantum #Tech",
                    "posted_at": "2026-09-08T10:00:00Z",
                    "metrics": {"likes": 50, "comments": 10},
                },
                {
                    "platform": "twitter",
                    "external_id": "raw_2",
                    "text": "Quantum computing qubit fidelity reaches new milestones. #Quantum",
                    "posted_at": "2026-09-08T11:00:00Z",
                    "metrics": {"likes": 90, "comments": 25},
                },
            ]
        }
        code, data = call_api("POST", "/api/v1/analytics/engine/analyze", payload)
        self.assertEqual(code, 200)
        self.assertEqual(data["total_posts_evaluated"], 2)
        self.assertGreater(data["engagement_analytics"]["total_likes"], 0)

    def test_4_analyze_with_ad_hoc_text(self):
        """Test POST /api/v1/analytics/engine/analyze with single ad-hoc text string."""
        payload = {"text": "Exciting launch of InsightX Phase 4.7 API! #InsightX #Launch"}
        code, data = call_api("POST", "/api/v1/analytics/engine/analyze", payload)
        self.assertEqual(code, 200)
        self.assertEqual(data["total_posts_evaluated"], 1)

    def test_5_specialized_engagement_endpoint(self):
        """Test POST /api/v1/analytics/engine/engagement."""
        payload = {"posts": self.sample_posts}
        code, data = call_api("POST", "/api/v1/analytics/engine/engagement", payload)
        self.assertEqual(code, 200)
        self.assertIn("overall", data)
        self.assertIn("distribution", data)
        self.assertIn("virality", data)
        self.assertIn("discussion", data)
        self.assertIn("platform_comparison", data)
        self.assertEqual(data["overall"]["total_posts"], 4)

    def test_6_specialized_sentiment_endpoint(self):
        """Test POST /api/v1/analytics/engine/sentiment."""
        payload = {"posts": self.sample_posts, "interval_unit": "hour"}
        code, data = call_api("POST", "/api/v1/analytics/engine/sentiment", payload)
        self.assertEqual(code, 200)
        self.assertIn("overall_distribution", data)
        self.assertIn("platform_sentiment", data)
        self.assertIn("temporal_sentiment", data)
        self.assertIn("top_positive_posts", data)
        self.assertIn("top_negative_posts", data)

    def test_7_specialized_trends_endpoint(self):
        """Test POST /api/v1/analytics/engine/trends."""
        payload = {"posts": self.sample_posts, "top_k": 2}
        code, data = call_api("POST", "/api/v1/analytics/engine/trends", payload)
        self.assertEqual(code, 200)
        self.assertIn("ranked_trends", data)
        self.assertIn("top_spiking_trends", data)
        self.assertIn("platform_trends", data)
        self.assertLessEqual(len(data["ranked_trends"]), 2)

    def test_8_specialized_narratives_endpoint(self):
        """Test POST /api/v1/analytics/engine/narratives."""
        payload = {"posts": self.sample_posts, "top_k": 2}
        code, data = call_api("POST", "/api/v1/analytics/engine/narratives", payload)
        self.assertEqual(code, 200)
        self.assertIn("ranked_narratives", data)
        self.assertIn("cross_platform_narratives", data)
        self.assertLessEqual(len(data["ranked_narratives"]), 2)


    def test_9_specialized_time_series_endpoint(self):
        """Test POST /api/v1/analytics/engine/time-series."""
        payload = {
            "posts": self.sample_posts,
            "interval_unit": "hour",
            "rolling_window_size": 2,
            "anomaly_threshold_z": 2.0,
        }
        code, data = call_api("POST", "/api/v1/analytics/engine/time-series", payload)
        self.assertEqual(code, 200)
        self.assertEqual(data["interval_unit"], "hour")
        self.assertGreaterEqual(data["total_buckets"], 1)
        self.assertIn("buckets", data)

    def test_10_temporal_and_platform_filtering(self):
        """Test that start_time, end_time, and platform_filter restrict posts correctly."""
        payload = {
            "posts": self.sample_posts,
            "start_time": "2026-09-08T10:30:00Z",
            "end_time": "2026-09-08T12:30:00Z",
            "platform_filter": ["twitter"],
        }
        code, data = call_api("POST", "/api/v1/analytics/engine/analyze", payload)
        self.assertEqual(code, 200)
        # Should only match p2 (11:00 on twitter)
        self.assertEqual(data["total_posts_evaluated"], 1)

    def test_11_request_validation_errors(self):
        """Test 400 and 422 HTTP validation errors."""
        # Empty payload
        code, data = call_api("POST", "/api/v1/analytics/engine/analyze", {})
        self.assertEqual(code, 400)
        self.assertIn("No post content provided", data["detail"])

        # Empty posts list
        code, data = call_api("POST", "/api/v1/analytics/engine/analyze", {"posts": []})
        self.assertEqual(code, 400)
        self.assertIn("Empty post list provided", data["detail"])

        # Reversed start_time and end_time
        code, data = call_api(
            "POST",
            "/api/v1/analytics/engine/analyze",
            {
                "posts": self.sample_posts,
                "start_time": "2026-09-08T15:00:00Z",
                "end_time": "2026-09-08T10:00:00Z",
            },
        )
        self.assertEqual(code, 400)
        self.assertIn("start_time cannot be after end_time", data["detail"])

        # Invalid interval (FastAPI Pydantic validation -> 422)
        code, data = call_api(
            "POST",
            "/api/v1/analytics/engine/analyze",
            {"posts": self.sample_posts, "interval_unit": "decade"},
        )
        self.assertEqual(code, 422)

        # Invalid rolling_window_size (ge=1 -> 0 triggers 422)
        code, data = call_api(
            "POST",
            "/api/v1/analytics/engine/analyze",
            {"posts": self.sample_posts, "rolling_window_size": 0},
        )
        self.assertEqual(code, 422)

    def test_12_server_error_handling_sanitizes_exceptions(self):
        """Test that unexpected internal failures return 500 without leaking stack traces."""
        with patch(
            "app.services.analytics_engine.service.AnalyticsEngineService.analyze",
            side_effect=RuntimeError("Secret internal database crash!"),
        ):
            code, data = call_api(
                "POST",
                "/api/v1/analytics/engine/analyze",
                {"posts": self.sample_posts},
            )
            self.assertEqual(code, 500)
            self.assertEqual(data["detail"], "An error occurred during analytics engine processing.")
            # Ensure internal secret exception message is not leaked
            self.assertNotIn("Secret internal database crash", json.dumps(data))


if __name__ == "__main__":
    unittest.main()
