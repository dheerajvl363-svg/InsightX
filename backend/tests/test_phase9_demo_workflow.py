import asyncio
import json
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from app.main import app
from app.schemas.intelligence import DemoProvenance


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


class TestPhase9DemoWorkflow(unittest.TestCase):
    """
    Comprehensive verification of the POST /api/v1/intelligence/demo/analyze-posts endpoint.
    Tests single & multi-post inputs, context assembly, provenance, deterministic analytics,
    evidence preservation, AI integration, and validation boundaries.
    """

    def test_01_single_x_post_success(self):
        """1. One X post successfully processed."""
        payload = {
            "posts": [
                {
                    "text": "Cybersecurity vulnerability detected in major payment gateway protocol.",
                    "platform": "X",
                    "author": "sec_researcher",
                    "likes": 200,
                    "reposts": 50,
                    "replies": 30,
                    "views": 5000,
                }
            ],
            "context_mode": "sample_stream",
            "persist_to_db": False,
            "include_ai": True,
        }
        status, res = call_api("POST", "/api/v1/intelligence/demo/analyze-posts", payload)
        self.assertEqual(status, 200, res)
        self.assertEqual(res["user_post_count"], 1)
        self.assertGreater(res["context_post_count"], 0)
        self.assertEqual(res["provenance"], DemoProvenance.USER_SUPPLIED.value)
        self.assertEqual(len(res["seed_posts"]), 1)
        self.assertEqual(res["seed_posts"][0]["author_username"], "sec_researcher")

    def test_02_multiple_x_posts_success(self):
        """2. Multiple X posts (e.g. 5 posts) processed in batch."""
        payload = {
            "posts": [
                {
                    "text": f"Telemetry update {i}: API latency spiked to {100 * i}ms in region eu-west.",
                    "author": f"infra_bot_{i}",
                    "likes": 10 * i,
                }
                for i in range(1, 6)
            ],
            "context_mode": "none",
            "persist_to_db": False,
            "include_ai": False,
        }
        status, res = call_api("POST", "/api/v1/intelligence/demo/analyze-posts", payload)
        self.assertEqual(status, 200, res)
        self.assertEqual(res["user_post_count"], 5)
        self.assertEqual(res["context_post_count"], 0)
        self.assertEqual(len(res["seed_posts"]), 5)

    def test_03_maximum_50_posts_accepted(self):
        """3. Maximum allowed batch of 50 posts is accepted."""
        payload = {
            "posts": [
                {
                    "text": f"Batch post index {i} reporting normal system operations.",
                    "author": "monitor",
                }
                for i in range(50)
            ],
            "context_mode": "none",
            "persist_to_db": False,
            "include_ai": False,
        }
        status, res = call_api("POST", "/api/v1/intelligence/demo/analyze-posts", payload)
        self.assertEqual(status, 200, res)
        self.assertEqual(res["user_post_count"], 50)

    def test_04_51_posts_rejected_validation_error(self):
        """4. 51 posts is rejected with HTTP 422 unprocessable entity."""
        payload = {
            "posts": [
                {
                    "text": f"Batch post index {i}",
                    "author": "monitor",
                }
                for i in range(51)
            ],
            "context_mode": "none",
            "persist_to_db": False,
        }
        status, res = call_api("POST", "/api/v1/intelligence/demo/analyze-posts", payload)
        self.assertEqual(status, 422)

    def test_05_empty_posts_batch_rejected(self):
        """5. Empty batch (0 posts) is rejected with HTTP 422."""
        payload = {
            "posts": [],
            "context_mode": "none",
        }
        status, res = call_api("POST", "/api/v1/intelligence/demo/analyze-posts", payload)
        self.assertEqual(status, 422)

    def test_06_sample_context_mode(self):
        """6. Sample context mode loads mock background posts."""
        payload = {
            "posts": [
                {
                    "text": "Evaluating local event against historical sample stream context.",
                    "author": "analyst",
                }
            ],
            "context_mode": "sample_stream",
            "persist_to_db": False,
            "include_ai": False,
        }
        status, res = call_api("POST", "/api/v1/intelligence/demo/analyze-posts", payload)
        self.assertEqual(status, 200, res)
        self.assertEqual(res["context_mode"], "sample_stream")
        self.assertGreater(res["context_post_count"], 30)
        self.assertEqual(res["total_context_size"], res["user_post_count"] + res["context_post_count"])

    def test_07_database_context_mode(self):
        """7. Database context mode correctly handled."""
        payload = {
            "posts": [
                {
                    "text": "Evaluating post against database context.",
                    "author": "analyst",
                }
            ],
            "context_mode": "database",
            "persist_to_db": False,
            "include_ai": False,
        }
        status, res = call_api("POST", "/api/v1/intelligence/demo/analyze-posts", payload)
        self.assertEqual(status, 200, res)
        self.assertEqual(res["context_mode"], "database")

    def test_08_no_context_mode(self):
        """8. No-context mode evaluates strictly user-supplied posts without crashing."""
        payload = {
            "posts": [
                {
                    "text": "Isolated standalone post without any background context.",
                    "author": "solo_author",
                }
            ],
            "context_mode": "none",
            "persist_to_db": False,
            "include_ai": False,
        }
        status, res = call_api("POST", "/api/v1/intelligence/demo/analyze-posts", payload)
        self.assertEqual(status, 200, res)
        self.assertEqual(res["context_post_count"], 0)
        self.assertEqual(res["total_context_size"], 1)

    def test_09_user_provenance_preserved(self):
        """9. User provenance is strictly tagged as 'user_supplied'."""
        payload = {
            "posts": [
                {
                    "text": "Auditable post checking provenance integrity.",
                    "author": "auditor",
                }
            ],
            "context_mode": "none",
            "persist_to_db": False,
        }
        status, res = call_api("POST", "/api/v1/intelligence/demo/analyze-posts", payload)
        self.assertEqual(status, 200, res)
        self.assertEqual(res["provenance"], "user_supplied")
        self.assertEqual(res["seed_posts"][0]["provenance"], "user_supplied")
        self.assertTrue(res["seed_posts"][0]["is_user_seed"])

    def test_10_sample_provenance_preserved(self):
        """10. Sample posts are separated and distinct from user posts."""
        payload = {
            "posts": [
                {"text": "Comparing user input with sample stream.", "author": "tester"}
            ],
            "context_mode": "sample_stream",
            "persist_to_db": False,
        }
        status, res = call_api("POST", "/api/v1/intelligence/demo/analyze-posts", payload)
        self.assertEqual(status, 200, res)
        self.assertEqual(res["user_post_count"], 1)
        self.assertGreater(res["context_post_count"], 0)
        # Seed posts should only contain user posts
        self.assertEqual(len(res["seed_posts"]), 1)

    def test_11_persistence_enabled_with_warning_on_offline(self):
        """11. Persistence enabled gracefully falls back if live DB is unavailable."""
        payload = {
            "posts": [
                {"text": "Post attempting persistence.", "author": "persister"}
            ],
            "context_mode": "none",
            "persist_to_db": True,
        }
        status, res = call_api("POST", "/api/v1/intelligence/demo/analyze-posts", payload)
        self.assertEqual(status, 200, res)
        self.assertIn("persisted", res)

    def test_12_persistence_disabled(self):
        """12. Persistence disabled does not persist to database."""
        payload = {
            "posts": [
                {"text": "Post with persist_to_db False.", "author": "ephemeral"}
            ],
            "context_mode": "none",
            "persist_to_db": False,
        }
        status, res = call_api("POST", "/api/v1/intelligence/demo/analyze-posts", payload)
        self.assertEqual(status, 200, res)
        self.assertFalse(res["persisted"])

    def test_13_existing_duplicate_handling(self):
        """13. Submitting the same post twice in a request succeeds."""
        payload = {
            "posts": [
                {"text": "Identical post text for deduplication check.", "author": "clone"},
                {"text": "Identical post text for deduplication check.", "author": "clone"},
            ],
            "context_mode": "none",
            "persist_to_db": False,
        }
        status, res = call_api("POST", "/api/v1/intelligence/demo/analyze-posts", payload)
        self.assertEqual(status, 200, res)
        self.assertEqual(res["user_post_count"], 2)

    def test_14_unified_workflow_is_invoked(self):
        """14. Unified workflow report is generated and present."""
        payload = {
            "posts": [{"text": "Checking unified intelligence invocation.", "author": "tester"}],
            "context_mode": "sample_stream",
            "persist_to_db": False,
        }
        status, res = call_api("POST", "/api/v1/intelligence/demo/analyze-posts", payload)
        self.assertEqual(status, 200, res)
        self.assertIn("unified_report", res)
        self.assertIn("analytics_summary", res["unified_report"])
        self.assertIn("batch_insights", res["unified_report"])

    def test_15_deterministic_insights_are_returned(self):
        """15. Deterministic insights are synthesized."""
        payload = {
            "posts": [
                {"text": "Cloud service outage causes severe disruptions.", "author": "reporter"}
            ],
            "context_mode": "sample_stream",
            "persist_to_db": False,
        }
        status, res = call_api("POST", "/api/v1/intelligence/demo/analyze-posts", payload)
        self.assertEqual(status, 200, res)
        insights = res["unified_report"]["batch_insights"]["insights"]
        self.assertIsInstance(insights, list)

    def test_16_evidence_references_are_preserved(self):
        """16. Evidence references are present on generated insights."""
        payload = {
            "posts": [{"text": "Testing evidence tracing.", "author": "trace_tester"}],
            "context_mode": "sample_stream",
            "persist_to_db": False,
        }
        status, res = call_api("POST", "/api/v1/intelligence/demo/analyze-posts", payload)
        self.assertEqual(status, 200, res)
        insights = res["unified_report"]["batch_insights"]["insights"]
        if insights:
            self.assertIn("evidence", insights[0])
            self.assertIn("raw_signals", insights[0]["evidence"])

    def test_17_ai_enabled_with_mock_provider(self):
        """17. AI interpretation is synthesized when include_ai=True on a seed-grounded signal."""
        payload = {
            "posts": [
                {"text": "Payment gateway cluster 1 failing transactions across all users.", "author": "dev1"},
                {"text": "Payment gateway cluster 2 timeout errors spiking rapidly.", "author": "dev2"},
                {"text": "Payment gateway outage confirmed by merchant services.", "author": "dev3"},
            ],
            "context_mode": "sample_stream",
            "persist_to_db": False,
            "include_ai": True,
        }
        status, res = call_api("POST", "/api/v1/intelligence/demo/analyze-posts", payload)
        self.assertEqual(status, 200, res)
        self.assertTrue(res["is_seed_grounded"])
        self.assertIsNotNone(res["primary_insight"])
        self.assertIsNotNone(res["primary_ai_interpretation"])

    def test_18_ai_disabled(self):
        """18. AI interpretation is None when include_ai=False."""
        payload = {
            "posts": [{"text": "AI disabled run.", "author": "no_ai"}],
            "context_mode": "sample_stream",
            "persist_to_db": False,
            "include_ai": False,
        }
        status, res = call_api("POST", "/api/v1/intelligence/demo/analyze-posts", payload)
        self.assertEqual(status, 200, res)
        self.assertIsNone(res.get("primary_ai_interpretation"))

    def test_19_ai_failure_fallback(self):
        """19. AI failure gracefully records a warning without breaking analysis."""
        with patch("app.services.intelligence.demo.AIAssistedIntelligenceService.analyze_insight", side_effect=RuntimeError("Simulated LLM network failure")):
            payload = {
                "posts": [
                    {"text": "Payment gateway cluster 1 failing transactions.", "author": "dev1"},
                    {"text": "Payment gateway cluster 2 timeout errors.", "author": "dev2"},
                    {"text": "Payment gateway outage confirmed.", "author": "dev3"},
                ],
                "context_mode": "sample_stream",
                "persist_to_db": False,
                "include_ai": True,
            }
            status, res = call_api("POST", "/api/v1/intelligence/demo/analyze-posts", payload)
            self.assertEqual(status, 200, res)
            self.assertTrue(res["is_seed_grounded"])
            self.assertIsNone(res.get("primary_ai_interpretation"))
            self.assertTrue(any("AI qualitative interpretation unavailable" in w for w in res["warnings"]))

    def test_20_invalid_input_rejected_422(self):
        """20. Invalid payload rejected with 422."""
        # Empty text
        payload = {
            "posts": [{"text": "   ", "author": "bad"}],
            "context_mode": "none",
        }
        status, res = call_api("POST", "/api/v1/intelligence/demo/analyze-posts", payload)
        self.assertEqual(status, 422)

        # Invalid context mode
        payload_bad_mode = {
            "posts": [{"text": "Valid text", "author": "valid"}],
            "context_mode": "unsupported_mode_123",
        }
        status2, res2 = call_api("POST", "/api/v1/intelligence/demo/analyze-posts", payload_bad_mode)
        self.assertEqual(status2, 422)

    def test_21_no_context_single_post_does_not_crash(self):
        """21. Single post with context_mode='none' does not crash."""
        payload = {
            "posts": [{"text": "Single post with absolutely no historical context.", "author": "solo"}],
            "context_mode": "none",
            "persist_to_db": False,
            "include_ai": False,
        }
        status, res = call_api("POST", "/api/v1/intelligence/demo/analyze-posts", payload)
        self.assertEqual(status, 200, res)
        self.assertEqual(res["total_context_size"], 1)

    def test_22_supporting_post_ids_preserved(self):
        """22. Seed posts preserve generated external_post_ids."""
        payload = {
            "posts": [{"text": "Checking ID preservation.", "author": "id_tester"}],
            "context_mode": "none",
            "persist_to_db": False,
        }
        status, res = call_api("POST", "/api/v1/intelligence/demo/analyze-posts", payload)
        self.assertEqual(status, 200, res)
        self.assertTrue(bool(res["seed_posts"][0]["external_post_id"]))

    def test_23_frontend_required_response_fields_present(self):
        """23. All frontend required fields exist on response."""
        payload = {
            "posts": [{"text": "Frontend contract validation post.", "author": "fe_dev"}],
            "context_mode": "sample_stream",
            "persist_to_db": False,
            "include_ai": True,
        }
        status, res = call_api("POST", "/api/v1/intelligence/demo/analyze-posts", payload)
        self.assertEqual(status, 200, res)

        required_keys = [
            "seed_posts",
            "provenance",
            "user_post_count",
            "context_post_count",
            "total_context_size",
            "context_mode",
            "persisted",
            "unified_report",
            "is_seed_grounded",
            "primary_insight",
            "ambient_insight",
            "warnings",
            "executed_at",
        ]
        for key in required_keys:
            self.assertIn(key, res, f"Missing required response field: {key}")

    def test_24_single_post_sample_context_not_labeled_seed_grounded(self):
        """24. Phase 9.10: Single post with sample context must have is_seed_grounded=False, primary_insight=None."""
        payload = {
            "posts": [{"text": "Single isolated post on payment gateway issues.", "author": "solo_user"}],
            "context_mode": "sample_stream",
            "persist_to_db": False,
            "include_ai": True,
        }
        status, res = call_api("POST", "/api/v1/intelligence/demo/analyze-posts", payload)
        self.assertEqual(status, 200, res)
        self.assertFalse(res["is_seed_grounded"])
        self.assertIsNone(res["primary_insight"])
        self.assertIsNotNone(res["ambient_insight"])
        self.assertIsNone(res.get("primary_ai_interpretation"))

    def test_25_multiple_posts_yield_genuine_seed_grounded_insight(self):
        """25. Phase 9.10: Multiple related posts trigger genuine seed-grounded insight and AI interpretation."""
        payload = {
            "posts": [
                {"text": "Cloud service outage: database connections timing out #outage", "author": "admin1"},
                {"text": "Database cluster outage confirmed in region 1. Latency spiking.", "author": "admin2"},
                {"text": "Failover outage in database proxy causing elevated 500 errors.", "author": "admin3"},
            ],
            "context_mode": "sample_stream",
            "persist_to_db": False,
            "include_ai": True,
        }
        status, res = call_api("POST", "/api/v1/intelligence/demo/analyze-posts", payload)
        self.assertEqual(status, 200, res)
        self.assertTrue(res["is_seed_grounded"])
        self.assertIsNotNone(res["primary_insight"])
        self.assertIsNone(res["ambient_insight"])
        self.assertIsNotNone(res.get("primary_ai_interpretation"))
        # Evidence post IDs or external IDs must overlap with user seed posts
        seed_ext_ids = {s["external_post_id"] for s in res["seed_posts"]}
        evidence_ext = set(res["primary_insight"]["evidence"]["external_post_ids"])
        self.assertTrue(bool(seed_ext_ids.intersection(evidence_ext)))
