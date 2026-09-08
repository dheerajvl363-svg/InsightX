import asyncio
from datetime import datetime, timedelta, timezone
import json
import unittest

from app.main import app
from app.schemas.post import RawPostPayload
from app.services.intelligence.workflow import (
    UnifiedIntelligenceWorkflow,
    get_unified_workflow,
)


def call_api(method: str, full_path: str, body: dict = None) -> tuple[int, dict]:
    """Native ASGI HTTP request runner for FastAPI testing."""
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


class TestPhase7UnifiedWorkflow(unittest.TestCase):
    """
    Focused Integration Test Suite for Phase 7.2.6: Unified Intelligence Workflow.
    Validates end-to-end pipeline:
    Raw Data → Analytics → Detection → Explanations → Evidence Traceability → API.
    """

    def setUp(self):
        self.workflow = get_unified_workflow()
        now = datetime.now(timezone.utc)

        # Seed realistic social posts covering multi-platform, sentiment polarity, and recurring topic
        self.sample_raw_posts = [
            RawPostPayload(
                platform="x",
                external_id="wf_p1",
                text="The database migration v4.0 is a complete disaster. Total failure and data loss.",
                author_username="sysadmin_bob",
                posted_at=now - timedelta(minutes=45),
            ),
            RawPostPayload(
                platform="x",
                external_id="wf_p2",
                text="Major database migration outage in production. Service completely broken and unusable.",
                author_username="dev_carol",
                posted_at=now - timedelta(minutes=40),
            ),
            RawPostPayload(
                platform="reddit",
                external_id="wf_p3",
                text="Critical warning: database migration breaks replica consistency! Avoid at all costs.",
                author_username="db_expert",
                posted_at=now - timedelta(minutes=35),
            ),
            RawPostPayload(
                platform="telegram",
                external_id="wf_p4",
                text="Terrible database migration bug hit our cluster too. Everything failed.",
                author_username="tele_lead",
                posted_at=now - timedelta(minutes=30),
            ),
            RawPostPayload(
                platform="x",
                external_id="wf_p5",
                text="Database migration failure confirmed. Downgrading immediately.",
                author_username="tech_guy",
                posted_at=now - timedelta(minutes=25),
            ),
            RawPostPayload(
                platform="reddit",
                external_id="wf_p6",
                text="Database migration rollback underway. Horrible release.",
                author_username="sre_dave",
                posted_at=now - timedelta(minutes=20),
            ),
        ]

    def test_1_empty_dataset_handling(self):
        """Verifies that an empty dataset safely yields an empty report without exceptions."""
        res = self.workflow.run_workflow(posts=[], raw_posts=[])
        self.assertEqual(res.total_insights, 0)
        self.assertEqual(res.total_explanations, 0)
        self.assertEqual(len(res.batch_insights.insights), 0)
        self.assertEqual(len(res.explanations), 0)
        self.assertEqual(res.analytics_summary["total_posts"], 0)

    def test_2_raw_posts_to_traceable_intelligence(self):
        """
        Verifies the full pipeline:
        RawPostPayloads
        → DataNormalizer
        → Sentiment/Topic/Trend/Network analytics
        → Deterministic Intelligence Detection
        → Explanations & Evidence References
        """
        res = self.workflow.run_workflow(
            raw_posts=self.sample_raw_posts,
            generate_explanations=True,
            min_confidence=0.5,
        )

        self.assertGreater(res.total_insights, 0)
        self.assertGreater(res.total_explanations, 0)
        self.assertEqual(len(res.batch_insights.insights), res.total_insights)
        self.assertEqual(len(res.explanations), res.total_explanations)

        # Check analytics summary
        self.assertEqual(res.analytics_summary["total_posts"], 6)
        self.assertIn("X", res.analytics_summary["platforms_detected"])
        self.assertIn("Reddit", res.analytics_summary["platforms_detected"])
        self.assertIn("Telegram", res.analytics_summary["platforms_detected"])

        # Check that explanations match insights 1:1
        insight_ids = {item.id for item in res.batch_insights.insights}
        explanation_insight_ids = {expl.insight_id for expl in res.explanations}
        self.assertEqual(insight_ids, explanation_insight_ids)

        # Verify evidence references and audit trail
        for expl in res.explanations:
            self.assertTrue(len(expl.facts) > 0)
            self.assertTrue(len(expl.interpretation) > 0)
            self.assertTrue(len(expl.confidence_rationale) > 0)
            self.assertTrue(len(expl.severity_rationale) > 0)
            self.assertIsNotNone(expl.evidence_references)

    def test_3_sentiment_shift_evidence_traceability_closure(self):
        """
        Confirms that Phase 7.2.6 explicitly closed the sentiment-shift evidence traceability gap:
        evidence must contain post_ids or external_post_ids and platforms.
        """
        res = self.workflow.run_workflow(
            raw_posts=self.sample_raw_posts,
            generate_explanations=True,
        )

        sentiment_insights = [
            item for item in res.batch_insights.insights
            if item.type.value == "sentiment_shift"
        ]
        self.assertTrue(len(sentiment_insights) > 0, "Expected sentiment_shift insight for negative post batch")

        insight = sentiment_insights[0]
        # Evidence must have external_post_ids and platforms populated
        self.assertTrue(
            len(insight.evidence.external_post_ids) > 0 or len(insight.evidence.post_ids) > 0,
            "Sentiment shift evidence must contain supporting post IDs",
        )
        self.assertTrue(
            len(insight.evidence.platforms) > 0,
            "Sentiment shift evidence must contain supporting platform names",
        )
        self.assertIn("X", insight.evidence.platforms)

    def test_4_get_insight_explanation_lookup(self):
        """Verifies deterministic explanation lookup for a specific insight ID."""
        res = self.workflow.run_workflow(
            raw_posts=self.sample_raw_posts,
            generate_explanations=True,
        )
        target_insight = res.batch_insights.insights[0]

        # Fetch explanation by ID
        expl = self.workflow.get_insight_explanation(
            insight_id=target_insight.id,
            raw_posts=self.sample_raw_posts,
        )
        self.assertEqual(expl.insight_id, target_insight.id)
        self.assertEqual(expl.title, target_insight.title)
        self.assertEqual(expl.severity, target_insight.severity)

    def test_5_api_endpoints_via_unified_workflow(self):
        """Verifies FastAPI routing integration with UnifiedIntelligenceWorkflow."""
        # 1. GET /api/v1/intelligence/insights
        status, data = call_api("GET", "/api/v1/intelligence/insights")
        self.assertEqual(status, 200)
        self.assertIn("insights", data)
        self.assertIn("total_insights", data)

        # 2. GET /api/v1/intelligence/insights/unified
        status, data = call_api("GET", "/api/v1/intelligence/insights/unified")
        self.assertEqual(status, 200)
        self.assertIn("batch_insights", data)
        self.assertIn("explanations", data)
        self.assertIn("analytics_summary", data)

        # 3. POST /api/v1/intelligence/analyze with include_explanations=True
        payload = {
            "raw_posts": [p.model_dump(mode="json") for p in self.sample_raw_posts],
            "include_explanations": True,
        }
        status, data = call_api("POST", "/api/v1/intelligence/analyze", payload)
        self.assertEqual(status, 200)
        self.assertGreater(data["total_insights"], 0)
        first_insight = data["insights"][0]
        # Metadata must contain the synthesized explanation
        self.assertIn("explanation", first_insight["metadata"])
        self.assertEqual(first_insight["metadata"]["explanation"]["insight_id"], first_insight["id"])


if __name__ == "__main__":
    unittest.main()
