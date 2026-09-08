import asyncio
from datetime import datetime, timedelta, timezone
import json
import unittest

from app.main import app
from app.schemas.analytics_api import (
    CombinedAnalyticsResponse,
    CombinedAnalyzeRequest,
    DemographicAnalyzeRequest,
    EmotionAnalyzeRequest,
    SentimentAnalyzeRequest,
    TopicAnalyzeRequest,
    TrendAnalyzeRequest,
)
from app.schemas.data_quality import AnalyticsReadyPost
from app.schemas.demographic import BatchDemographicResult, DemographicProfile
from app.schemas.emotion import BatchEmotionResult
from app.schemas.post import RawPostPayload
from app.schemas.sentiment import BatchSentimentResult
from app.schemas.topic import BatchTopicResult
from app.schemas.trend import BatchTrendResult


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


class TestAnalyticsAPIEndpoints(unittest.TestCase):
    """
    Comprehensive test suite for Phase 3 Component 3.7: Analytics API.
    Tests HTTP routing, request/response models, error handling, and unified pipeline.
    """

    def setUp(self):
        self.base_time = "2026-09-08T12:00:00Z"
        self.sample_raw_posts = [
            {
                "platform": "x",
                "external_id": "api_p1",
                "text": "Hyderabad metro fares increased significantly today! #MetroFares",
                "posted_at": "2026-09-08T11:45:00Z",
                "metadata": {"demographics": {"age": 22, "gender": "female", "city": "Hyderabad"}},
            },
            {
                "platform": "x",
                "external_id": "api_p2",
                "text": "Metro ticket prices are getting very expensive and unaffordable.",
                "posted_at": "2026-09-08T11:50:00Z",
                "metadata": {"demographics": {"age": 28, "gender": "male", "city": "Hyderabad"}},
            },
            {
                "platform": "x",
                "external_id": "api_p3",
                "text": "Excited for the new AI hackathon! Wonderful opportunity for innovation.",
                "posted_at": "2026-09-08T11:55:00Z",
                "metadata": {"demographics": {"age": 21, "gender": "female", "city": "Bengaluru"}},
            },
        ]

    # 1. Health check
    def test_1_health_check(self):
        """Verifies GET /health endpoint operates cleanly."""
        status, data = call_api("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(data.get("status"), "ok")

    # 2. Sentiment Endpoint
    def test_2_sentiment_analysis_endpoint(self):
        """Tests POST /api/v1/analytics/sentiment with raw posts and text convenience."""
        # Batch raw posts
        payload = {"raw_posts": self.sample_raw_posts}
        status, data = call_api("POST", "/api/v1/analytics/sentiment", payload)
        self.assertEqual(status, 200)
        self.assertEqual(data["total_analyzed"], 3)
        self.assertIn("positive_count", data)
        self.assertIn("negative_count", data)
        self.assertEqual(len(data["results"]), 3)

        # Quick text inference
        text_payload = {"text": "This service is completely wonderful and delightful!"}
        status, data = call_api("POST", "/api/v1/analytics/sentiment", text_payload)
        self.assertEqual(status, 200)
        self.assertEqual(data["total_analyzed"], 1)
        self.assertEqual(data["positive_count"], 1)
        self.assertEqual(data["results"][0]["label"], "positive")

    # 3. Emotion Endpoint
    def test_3_emotion_analysis_endpoint(self):
        """Tests POST /api/v1/analytics/emotion with batch posts and text."""
        payload = {"raw_posts": self.sample_raw_posts}
        status, data = call_api("POST", "/api/v1/analytics/emotion", payload)
        self.assertEqual(status, 200)
        self.assertEqual(data["total_analyzed"], 3)
        self.assertIn("emotion_distribution", data)
        self.assertEqual(len(data["results"]), 3)

    # 4. Topics Endpoint
    def test_4_topics_extraction_endpoint(self):
        """Tests POST /api/v1/analytics/topics clustering and keyword extraction."""
        payload = {"raw_posts": self.sample_raw_posts}
        status, data = call_api("POST", "/api/v1/analytics/topics", payload)
        self.assertEqual(status, 200)
        self.assertEqual(data["total_posts_analyzed"], 3)
        self.assertGreaterEqual(data["total_topics_found"], 1)
        self.assertIsInstance(data["topics"], list)
        topic_labels = [t["label"].lower() for t in data["topics"]]
        self.assertTrue(any("metro" in l for l in topic_labels))

    # 5. Trends Endpoint
    def test_5_trends_detection_endpoint(self):
        """Tests POST /api/v1/analytics/trends temporal velocity calculation."""
        payload = {
            "raw_posts": self.sample_raw_posts,
            "reference_time": "2026-09-08T12:00:00Z",
            "window_duration_seconds": 3600,
        }
        status, data = call_api("POST", "/api/v1/analytics/trends", payload)
        self.assertEqual(status, 200)
        self.assertGreaterEqual(data["total_topics_evaluated"], 1)
        self.assertIsInstance(data["trends"], list)
        self.assertIn("trend_score", data["trends"][0])
        self.assertIn("direction", data["trends"][0])

    # 6. Demographics Endpoint
    def test_6_demographics_endpoint(self):
        """Tests POST /api/v1/analytics/demographics aggregation."""
        # Directly passing explicit demographic profiles
        profiles_payload = {
            "profiles": [
                {"age": 22, "gender": "female", "location": "Hyderabad, India"},
                {"age": 30, "gender": "male", "location": "Bengaluru, India"},
            ]
        }
        status, data = call_api("POST", "/api/v1/analytics/demographics", profiles_payload)
        self.assertEqual(status, 200)
        self.assertEqual(data["total_profiles_analyzed"], 2)
        dist = data["overall_distribution"]
        self.assertEqual(dist["age_groups"]["counts"]["18-24"], 1)
        self.assertEqual(dist["age_groups"]["counts"]["25-34"], 1)
        self.assertEqual(dist["gender"]["counts"]["female"], 1)

        # Passing raw posts with embedded metadata
        raw_payload = {"raw_posts": self.sample_raw_posts}
        status, data = call_api("POST", "/api/v1/analytics/demographics", raw_payload)
        self.assertEqual(status, 200)
        self.assertEqual(data["total_profiles_analyzed"], 3)

    # 7. Unified Pipeline (/analyze)
    def test_7_combined_analyze_pipeline(self):
        """Tests POST /api/v1/analytics/analyze orchestrating the entire Phase 3 stack."""
        payload = {
            "raw_posts": self.sample_raw_posts,
            "reference_time": "2026-09-08T12:00:00Z",
            "include_sentiment": True,
            "include_emotion": True,
            "include_topics": True,
            "include_trends": True,
            "include_demographics": True,
        }
        status, data = call_api("POST", "/api/v1/analytics/analyze", payload)
        self.assertEqual(status, 200)
        self.assertEqual(data["total_posts_evaluated"], 3)
        self.assertEqual(data["valid_posts_count"], 3)

        # Verify all sub-components ran and attached structured results
        self.assertIsNotNone(data["data_quality"])
        self.assertIsNotNone(data["sentiment"])
        self.assertIsNotNone(data["emotion"])
        self.assertIsNotNone(data["topics"])
        self.assertIsNotNone(data["trends"])
        self.assertIsNotNone(data["demographics"])

        self.assertEqual(data["sentiment"]["total_analyzed"], 3)
        self.assertEqual(data["emotion"]["total_analyzed"], 3)
        self.assertGreaterEqual(data["topics"]["total_topics_found"], 1)
        self.assertGreaterEqual(data["trends"]["total_topics_evaluated"], 1)
        self.assertEqual(data["demographics"]["total_profiles_analyzed"], 3)

    # 8. Error Handling
    def test_8_error_handling(self):
        """Tests proper HTTP status codes for empty, malformed, or invalid payloads."""
        # Empty payload
        status, data = call_api("POST", "/api/v1/analytics/sentiment", {})
        self.assertEqual(status, 400)
        self.assertIn("detail", data)

        # Invalid JSON type
        status, data = call_api("POST", "/api/v1/analytics/sentiment", {"raw_posts": "not_a_list"})
        self.assertEqual(status, 422)

        # Invalid field types in /analyze
        status, data = call_api("POST", "/api/v1/analytics/analyze", {"include_sentiment": "not_a_bool"})
        self.assertEqual(status, 422)

    # 9. OpenAPI Schema Generation
    def test_9_openapi_documentation_schema(self):
        """Verifies OpenAPI JSON schema generates successfully and registers analytics routes."""
        status, data = call_api("GET", "/openapi.json")
        self.assertEqual(status, 200)
        self.assertIn("paths", data)

        paths = data["paths"]
        self.assertIn("/api/v1/analytics/sentiment", paths)
        self.assertIn("/api/v1/analytics/emotion", paths)
        self.assertIn("/api/v1/analytics/topics", paths)
        self.assertIn("/api/v1/analytics/trends", paths)
        self.assertIn("/api/v1/analytics/demographics", paths)
        self.assertIn("/api/v1/analytics/analyze", paths)

    # 10. Selective Pipeline Execution
    def test_10_selective_analyze_pipeline(self):
        """Verifies that flags disable unrequested sub-services in /analyze."""
        payload = {
            "raw_posts": self.sample_raw_posts,
            "include_sentiment": True,
            "include_emotion": False,
            "include_topics": False,
            "include_trends": False,
            "include_demographics": False,
        }
        status, data = call_api("POST", "/api/v1/analytics/analyze", payload)
        self.assertEqual(status, 200)
        self.assertIsNotNone(data["sentiment"])
        self.assertIsNone(data["emotion"])
        self.assertIsNone(data["topics"])
        self.assertIsNone(data["trends"])
        self.assertIsNone(data["demographics"])

    # 11. Mock Service Dependency Injection via app.dependency_overrides
    def test_11_mock_service_dependency_override(self):
        """Verifies FastAPI dependency injection override works for testing with mock services."""
        from app.api.routes.analytics import get_sentiment_service
        from app.schemas.sentiment import SentimentLabel, SentimentProbabilities, SentimentResult
        from app.services.sentiment.base import BaseSentimentEngine

        class MockEngine(BaseSentimentEngine):
            @property
            def model_name(self) -> str:
                return "mock-sentiment-api-v1"

            def analyze_text(self, text: str):
                from app.services.sentiment.base import SentimentInferenceResult
                return SentimentInferenceResult(
                    label=SentimentLabel.POSITIVE,
                    score=0.99,
                    confidence=1.0,
                    probabilities=SentimentProbabilities(positive=0.99, neutral=0.01, negative=0.0),
                    model_name="mock-sentiment-api-v1",
                )


            def analyze_batch(self, texts):
                return [self.analyze_text(t) for t in texts]

        from app.services.sentiment.service import SentimentAnalysisService
        mock_svc = SentimentAnalysisService(engine=MockEngine())

        app.dependency_overrides[get_sentiment_service] = lambda: mock_svc
        try:
            status, data = call_api("POST", "/api/v1/analytics/sentiment", {"text": "Any text"})
            self.assertEqual(status, 200)
            self.assertEqual(data["results"][0]["model"], "mock-sentiment-api-v1")
            self.assertEqual(data["results"][0]["score"], 0.99)
        finally:
            app.dependency_overrides.pop(get_sentiment_service, None)


if __name__ == "__main__":
    unittest.main()

