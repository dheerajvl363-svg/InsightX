import asyncio
import json
import unittest
from datetime import datetime, timezone

from app.main import app

def call_api(method: str, full_path: str, body: dict = None) -> tuple[int, dict]:
    """
    Executes a native ASGI HTTP request against the FastAPI application.
    Tests full FastAPI pipeline: routing, dependency injection, validation, and serialization.
    """
    if "?" in full_path:
        path, query = full_path.split("?", 1)
        query_string = query.encode("utf-8")
    else:
        path = full_path
        query_string = b""
        
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
        "query_string": query_string,
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

class TestPhase7IntelligenceAPI(unittest.TestCase):
    """
    Comprehensive test suite for Phase 7.2.4: Intelligence API Integration.
    Tests HTTP routing, request/response models, error handling, and traceability.
    """

    def setUp(self):
        self.sample_raw_posts = [
            {
                "platform": "x",
                "external_id": "api_p1",
                "text": "The new update is absolutely terrible and breaks everything!",
                "posted_at": "2026-09-08T11:45:00Z",
            },
            {
                "platform": "x",
                "external_id": "api_p2",
                "text": "Completely broken update. Downgrading immediately.",
                "posted_at": "2026-09-08T11:50:00Z",
            },
            {
                "platform": "x",
                "external_id": "api_p3",
                "text": "Worst update ever released. Fix it!",
                "posted_at": "2026-09-08T11:55:00Z",
            },
            {
                "platform": "telegram",
                "external_id": "api_p4",
                "text": "Update broke my system too.",
                "posted_at": "2026-09-08T11:56:00Z",
            },
            {
                "platform": "x",
                "external_id": "api_p5",
                "text": "The recent update is very bad.",
                "posted_at": "2026-09-08T11:57:00Z",
            },
            {
                "platform": "telegram",
                "external_id": "api_p6",
                "text": "Rolling back the latest update because it's terrible.",
                "posted_at": "2026-09-08T11:58:00Z",
            },
        ]

    def test_1_analyze_workflow_successful(self):
        """Tests POST /api/v1/intelligence/analyze with raw posts."""
        payload = {
            "raw_posts": self.sample_raw_posts,
            "min_confidence": 0.1
        }
        status, data = call_api("POST", "/api/v1/intelligence/analyze", payload)
        self.assertEqual(status, 200)
        
        self.assertIn("total_insights", data)
        self.assertIn("insights", data)
        self.assertIn("model", data)
        
        self.assertGreaterEqual(data["total_insights"], 1)
        
        # Verify traceability of evidence
        insight = data["insights"][0]
        self.assertIn("id", insight)
        self.assertIn("evidence", insight)
        self.assertIn("confidence", insight)
        
        # Should have cross-platform or sentiment shift due to negative posts
        self.assertTrue(len(insight["evidence"]["platforms"]) > 0 or insight["evidence"]["dominant_sentiment"] is not None)

    def test_2_analyze_invalid_payload(self):
        """Tests POST /api/v1/intelligence/analyze with missing required data."""
        payload = {
            "min_confidence": 0.5
        }
        status, data = call_api("POST", "/api/v1/intelligence/analyze", payload)
        self.assertEqual(status, 400)
        self.assertIn("Payload must contain", data["detail"])

    def test_3_get_insights_successful(self):
        """Tests GET /api/v1/intelligence/insights."""
        status, data = call_api("GET", "/api/v1/intelligence/insights")
        self.assertEqual(status, 200)
        
        self.assertIn("total_insights", data)
        self.assertIn("insights", data)
        self.assertIsInstance(data["insights"], list)

    def test_4_get_insights_filtering(self):
        """Tests GET /api/v1/intelligence/insights with platform filter."""
        # Note: query parameters in the path
        status, data = call_api("GET", "/api/v1/intelligence/insights?platform=X")
        self.assertEqual(status, 200)
        self.assertIsInstance(data.get("insights", []), list)

    def test_5_get_explanation_missing_id(self):
        """Tests GET /api/v1/intelligence/insights/{id}/explanation with a non-existent ID."""
        status, data = call_api("GET", "/api/v1/intelligence/insights/invalid_id_123/explanation")
        self.assertEqual(status, 404)
        self.assertIn("not found", data["detail"].lower())

    def test_6_get_explanation_successful(self):
        """Tests GET /api/v1/intelligence/insights/{id}/explanation with a valid ID from GET /insights."""
        # First get insights to find a valid ID
        status, data = call_api("GET", "/api/v1/intelligence/insights")
        self.assertEqual(status, 200)
        insights = data.get("insights", [])
        
        if len(insights) > 0:
            valid_id = insights[0]["id"]
            
            exp_status, exp_data = call_api("GET", f"/api/v1/intelligence/insights/{valid_id}/explanation")
            self.assertEqual(exp_status, 200)
            
            # Verify explanation structure
            self.assertEqual(exp_data["insight_id"], valid_id)
            self.assertIn("facts", exp_data)
            self.assertIn("interpretation", exp_data)
            self.assertIn("severity_rationale", exp_data)
            self.assertIn("evidence_references", exp_data)

    def test_7_get_insights_invalid_parameters(self):
        """Tests GET /api/v1/intelligence/insights with out of range confidence."""
        status, data = call_api("GET", "/api/v1/intelligence/insights?min_confidence=2.0")
        self.assertEqual(status, 422)

if __name__ == "__main__":
    unittest.main()
