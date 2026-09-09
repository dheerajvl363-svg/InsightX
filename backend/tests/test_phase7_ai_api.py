import asyncio
import json
import unittest
from unittest.mock import MagicMock, patch
import urllib.error

from app.api.routes.intelligence import get_workflow_instance
from app.main import app
from app.schemas.post import RawPostPayload
from app.services.intelligence.ai.schemas import AIInterpretationResponse
from app.services.intelligence.workflow import get_unified_workflow
from app.services.intelligence.ai.openai import OpenAIProvider
from app.services.intelligence.ai.service import AIAssistedIntelligenceService


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


class TestPhase7AIAPI(unittest.TestCase):
    """
    Test suite for Phase 7.3.4: AI Interpretation API & Unified Workflow Integration.
    Verifies endpoints, server-side bounding, graceful fallback, and backward compatibility.
    """

    def setUp(self):
        self.sample_raw_posts = [
            {
                "platform": "x",
                "external_id": "ai_api_p1",
                "text": "The latest service outage is completely unacceptable. System crashed.",
                "posted_at": "2026-09-08T11:45:00Z",
            },
            {
                "platform": "x",
                "external_id": "ai_api_p2",
                "text": "Completely broken update. System crashed again for everyone.",
                "posted_at": "2026-09-08T11:50:00Z",
            },
            {
                "platform": "x",
                "external_id": "ai_api_p3",
                "text": "Severe outages reported across multiple regions today. Fix it!",
                "posted_at": "2026-09-08T11:55:00Z",
            },
            {
                "platform": "telegram",
                "external_id": "ai_api_p4",
                "text": "Major crash detected. Services unavailable worldwide.",
                "posted_at": "2026-09-08T11:56:00Z",
            },
        ]

    def _get_valid_insight_id(self) -> str:
        status, analyze_data = call_api(
            "POST",
            "/api/v1/intelligence/analyze",
            {"raw_posts": self.sample_raw_posts, "min_confidence": 0.1},
        )
        self.assertEqual(status, 200)
        insights = analyze_data.get("insights", [])
        self.assertGreater(len(insights), 0, "Expected at least one insight for testing")
        return insights[0]["id"]

    def test_1_ai_interpret_successful_with_mock_provider(self):
        """Tests POST /api/v1/intelligence/insights/{insight_id}/ai-interpret returning 200 OK."""
        valid_id = self._get_valid_insight_id()
        payload = {
            "raw_posts": self.sample_raw_posts,
            "prompt_instructions": "Focus on critical infrastructure resilience",
            "max_post_ids": 15,
        }
        status, data = call_api("POST", f"/api/v1/intelligence/insights/{valid_id}/ai-interpret", payload)
        self.assertEqual(status, 200)

        self.assertEqual(data["insight_id"], valid_id)
        self.assertIn("insight", data)
        self.assertIn("explanation", data)
        self.assertIn("ai_analysis", data)
        self.assertFalse(data["is_fallback_used"])
        self.assertIn("generated_at", data)

        ai = data["ai_analysis"]
        self.assertEqual(ai["insight_id"], valid_id)
        self.assertTrue(len(ai["interpretation"]) > 0)
        self.assertIsInstance(ai["ai_recommendations"], list)
        self.assertIn("grounding_metadata", ai)
        self.assertIn("Deterministic analytics and evidence remain the source of truth", ai["disclaimer"])
        self.assertEqual(ai["provider_name"], "mock")

    def test_2_ai_interpret_unknown_insight_id(self):
        """Tests POST /api/v1/intelligence/insights/{insight_id}/ai-interpret with unknown ID returns 404."""
        status, data = call_api("POST", "/api/v1/intelligence/insights/non_existent_id_xyz/ai-interpret", {})
        self.assertEqual(status, 404)
        self.assertIn("not found", data["detail"].lower())

    def test_3_ai_interpret_server_side_validation_bounds(self):
        """Tests request validation rules: max_post_ids <= 50, prompt_instructions <= 500 chars."""
        valid_id = self._get_valid_insight_id()

        # max_post_ids > 50 should trigger 422
        status, data = call_api(
            "POST",
            f"/api/v1/intelligence/insights/{valid_id}/ai-interpret",
            {"max_post_ids": 100},
        )
        self.assertEqual(status, 422)

        # max_post_ids < 1 should trigger 422
        status, data = call_api(
            "POST",
            f"/api/v1/intelligence/insights/{valid_id}/ai-interpret",
            {"max_post_ids": 0},
        )
        self.assertEqual(status, 422)

        # prompt_instructions > 500 chars should trigger 422
        status, data = call_api(
            "POST",
            f"/api/v1/intelligence/insights/{valid_id}/ai-interpret",
            {"prompt_instructions": "A" * 501},
        )
        self.assertEqual(status, 422)

        # Valid bounds succeed
        status, data = call_api(
            "POST",
            f"/api/v1/intelligence/insights/{valid_id}/ai-interpret",
            {"raw_posts": self.sample_raw_posts, "prompt_instructions": "A" * 200, "max_post_ids": 10},
        )
        self.assertEqual(status, 200)

    def test_4_ai_interpret_graceful_fallback_on_provider_error(self):
        """Tests that when an AI provider fails or errors out, the endpoint returns 200 with is_fallback_used=True."""
        valid_id = self._get_valid_insight_id()

        with patch("urllib.request.urlopen") as mock_urlopen:
            # Simulate external LLM provider 500 internal server error
            mock_urlopen.side_effect = urllib.error.HTTPError(
                url="https://api.openai.com/v1/chat/completions",
                code=500,
                msg="Internal Server Error",
                hdrs={},
                fp=None,
            )

            # Create workflow configured with OpenAIProvider
            provider = OpenAIProvider(api_key="test-key-sk-xyz")
            failing_ai_service = AIAssistedIntelligenceService(provider=provider)

            workflow = get_unified_workflow()
            workflow.ai_service = failing_ai_service

            app.dependency_overrides[get_workflow_instance] = lambda: workflow
            try:
                status, data = call_api(
                    "POST",
                    f"/api/v1/intelligence/insights/{valid_id}/ai-interpret",
                    {"raw_posts": self.sample_raw_posts, "prompt_instructions": "Analyze fallback"},
                )

                self.assertEqual(status, 200, "Must never return 500 when AI fails")
                self.assertTrue(data["is_fallback_used"], "Expected fallback to be flagged")
                self.assertIn("ai_analysis", data)
                self.assertTrue(data["ai_analysis"]["is_flagged_unsupported"])
                self.assertEqual(data["ai_analysis"]["provider_name"], "openai")
                self.assertIn("Fallback", data["ai_analysis"]["interpretation"])
                # Deterministic insight & explanation must remain intact
                self.assertEqual(data["insight_id"], valid_id)
                self.assertIn("summary", data["insight"])
                self.assertIn("facts", data["explanation"])
            finally:
                app.dependency_overrides.clear()

    def test_5_unified_workflow_include_ai_flag(self):
        """Tests UnifiedIntelligenceWorkflow with include_ai=False vs include_ai=True."""
        workflow = get_unified_workflow()
        raw_payloads = [RawPostPayload(**p) for p in self.sample_raw_posts]

        # include_ai=False (default)
        res_no_ai = workflow.run_workflow(
            raw_posts=raw_payloads,
            min_confidence=0.1,
            generate_explanations=True,
            include_ai=False,
        )
        self.assertGreater(res_no_ai.total_insights, 0)
        self.assertEqual(len(res_no_ai.ai_analyses), 0)

        # include_ai=True
        res_with_ai = workflow.run_workflow(
            raw_posts=raw_payloads,
            min_confidence=0.1,
            generate_explanations=True,
            include_ai=True,
        )
        self.assertGreater(res_with_ai.total_insights, 0)
        self.assertEqual(len(res_with_ai.ai_analyses), len(res_with_ai.batch_insights.insights))
        for ai_item in res_with_ai.ai_analyses:
            self.assertTrue(hasattr(ai_item, "interpretation"))
            self.assertTrue(hasattr(ai_item, "grounding_metadata"))

    def test_6_analyze_endpoint_include_ai_metadata(self):
        """Tests POST /api/v1/intelligence/analyze with include_ai=True attaches ai_analysis metadata."""
        # include_ai = False
        payload_no_ai = {
            "raw_posts": self.sample_raw_posts,
            "min_confidence": 0.1,
            "include_ai": False,
        }
        status, data_no_ai = call_api("POST", "/api/v1/intelligence/analyze", payload_no_ai)
        self.assertEqual(status, 200)
        for insight in data_no_ai["insights"]:
            self.assertNotIn("ai_analysis", insight.get("metadata", {}))

        # include_ai = True
        payload_with_ai = {
            "raw_posts": self.sample_raw_posts,
            "min_confidence": 0.1,
            "include_ai": True,
        }
        status, data_with_ai = call_api("POST", "/api/v1/intelligence/analyze", payload_with_ai)
        self.assertEqual(status, 200)
        for insight in data_with_ai["insights"]:
            self.assertIn("ai_analysis", insight.get("metadata", {}))
            ai = insight["metadata"]["ai_analysis"]
            self.assertIn("interpretation", ai)
            self.assertIn("grounding_metadata", ai)
            self.assertEqual(ai["insight_id"], insight["id"])

    def test_7_backward_compatibility_endpoints(self):
        """Tests that GET /insights, GET /insights/{id}/explanation, and GET /insights/unified work unchanged."""
        # GET /insights
        status, data = call_api("GET", "/api/v1/intelligence/insights")
        self.assertEqual(status, 200)
        self.assertIn("total_insights", data)
        self.assertIn("insights", data)

        if data["insights"]:
            valid_id = data["insights"][0]["id"]
            # GET /insights/{id}/explanation
            exp_status, exp_data = call_api("GET", f"/api/v1/intelligence/insights/{valid_id}/explanation")
            self.assertEqual(exp_status, 200)
            self.assertEqual(exp_data["insight_id"], valid_id)
            self.assertIn("facts", exp_data)
            self.assertIn("interpretation", exp_data)

        # GET /insights/unified
        uni_status, uni_data = call_api("GET", "/api/v1/intelligence/insights/unified")
        self.assertEqual(uni_status, 200)
        self.assertIn("total_insights", uni_data)
        self.assertIn("analytics_summary", uni_data)
        self.assertIn("ai_analyses", uni_data)


if __name__ == "__main__":
    unittest.main()
