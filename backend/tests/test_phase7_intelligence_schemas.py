from datetime import datetime, timedelta, timezone
import json
import unittest

from pydantic import ValidationError

from app.schemas.intelligence import (
    BatchInsightResult,
    InsightEvidence,
    InsightItem,
    InsightSeverity,
    InsightStatus,
    InsightType,
    IntelligenceAnalyzeRequest,
)
from app.schemas.trend import TimeWindow


class TestPhase7IntelligenceSchemas(unittest.TestCase):
    """
    Unit test suite for Phase 7.2.1 Intelligence Data Model and Evidence Grounding Schemas.
    """

    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.window = TimeWindow(
            start=self.now - timedelta(hours=4),
            end=self.now,
        )

    def test_valid_insight_item_creation(self):
        evidence = InsightEvidence(
            topic_id="top_cyber_01",
            topic_label="Cybersecurity Threat Surge",
            growth_rate=145.5,
            current_volume=320,
            baseline_volume=130,
            z_score=3.42,
            sentiment_score=-0.45,
            dominant_sentiment="negative",
            post_ids=[101, 102, 103],
            external_post_ids=["x_post_1", "x_post_2"],
            key_authors=["threat_intel", "sec_guru"],
            platforms=["X", "Telegram"],
            time_window=self.window,
            raw_signals={"velocity": 4.5, "burst_ratio": 2.1},
        )

        insight = InsightItem(
            id="ins_20260909_001",
            type=InsightType.EMERGING_TREND,
            title="Coordinated Disinformation Campaign Detected",
            summary="Rapid volume surge observed across X and Telegram with anomalous negative sentiment trajectory.",
            severity=InsightSeverity.HIGH,
            confidence=0.92,
            affected_topic="Cybersecurity Threat Surge",
            affected_platforms=["X", "Telegram"],
            evidence=evidence,
            recommended_action="Initiate network entity clustering and isolate amplification nodes.",
            action_items=[
                "Cross-check top influencer handles in Network Graph",
                "Review evidence posts in Posts Explorer",
            ],
            status=InsightStatus.ACTIVE,
            metadata={"analyst_notes": "Correlates with recent CVE release"},
        )

        self.assertEqual(insight.id, "ins_20260909_001")
        self.assertEqual(insight.type, InsightType.EMERGING_TREND)
        self.assertEqual(insight.severity, InsightSeverity.HIGH)
        self.assertEqual(insight.confidence, 0.92)
        self.assertEqual(insight.status, InsightStatus.ACTIVE)
        self.assertEqual(len(insight.evidence.post_ids), 3)
        self.assertEqual(insight.evidence.z_score, 3.42)
        self.assertEqual(insight.evidence.dominant_sentiment, "negative")

    def test_insight_enums_validation(self):
        # Verify valid enum values
        self.assertEqual(InsightType.EMERGING_TREND.value, "emerging_trend")
        self.assertEqual(InsightType.ANOMALOUS_SPIKE.value, "anomalous_spike")
        self.assertEqual(InsightType.SENTIMENT_SHIFT.value, "sentiment_shift")
        self.assertEqual(InsightType.CROSS_PLATFORM_PROPAGATION.value, "cross_platform_propagation")
        self.assertEqual(InsightType.INFLUENCER_AMPLIFICATION.value, "influencer_amplification")
        self.assertEqual(InsightType.NARRATIVE_EMERGENCE.value, "narrative_emergence")
        self.assertEqual(InsightType.ENGAGEMENT_SURGE.value, "engagement_surge")
        self.assertEqual(InsightType.DATA_QUALITY_ALERT.value, "data_quality_alert")

        self.assertEqual(InsightSeverity.CRITICAL.value, "critical")
        self.assertEqual(InsightSeverity.HIGH.value, "high")
        self.assertEqual(InsightSeverity.MEDIUM.value, "medium")
        self.assertEqual(InsightSeverity.LOW.value, "low")
        self.assertEqual(InsightSeverity.INFO.value, "info")

        self.assertEqual(InsightStatus.ACTIVE.value, "active")
        self.assertEqual(InsightStatus.INVESTIGATING.value, "investigating")
        self.assertEqual(InsightStatus.RESOLVED.value, "resolved")
        self.assertEqual(InsightStatus.DISMISSED.value, "dismissed")

    def test_invalid_insight_type_raises(self):
        with self.assertRaises(ValidationError):
            InsightItem(
                id="ins_002",
                type="unsupported_custom_type",
                title="Invalid Type Insight",
                summary="Valid summary text describing something in detail.",
                confidence=0.8,
            )

    def test_invalid_severity_raises(self):
        with self.assertRaises(ValidationError):
            InsightItem(
                id="ins_003",
                type=InsightType.ANOMALOUS_SPIKE,
                title="Invalid Severity Insight",
                summary="Valid summary text describing something in detail.",
                severity="ultra_catastrophic",
                confidence=0.8,
            )

    def test_confidence_boundary_validation(self):
        # Confidence > 1.0 must fail
        with self.assertRaises(ValidationError):
            InsightItem(
                id="ins_004",
                type=InsightType.SENTIMENT_SHIFT,
                title="Out of Bounds Confidence",
                summary="Valid summary text describing something in detail.",
                confidence=1.05,
            )

        # Confidence < 0.0 must fail
        with self.assertRaises(ValidationError):
            InsightItem(
                id="ins_005",
                type=InsightType.SENTIMENT_SHIFT,
                title="Negative Confidence",
                summary="Valid summary text describing something in detail.",
                confidence=-0.1,
            )

        # Boundary values 0.0 and 1.0 must succeed
        item_zero = InsightItem(
            id="ins_zero",
            type=InsightType.DATA_QUALITY_ALERT,
            title="Zero Confidence",
            summary="Valid summary text describing something in detail.",
            confidence=0.0,
        )
        self.assertEqual(item_zero.confidence, 0.0)

        item_one = InsightItem(
            id="ins_one",
            type=InsightType.DATA_QUALITY_ALERT,
            title="Max Confidence",
            summary="Valid summary text describing something in detail.",
            confidence=1.0,
        )
        self.assertEqual(item_one.confidence, 1.0)

    def test_title_and_summary_length_validation(self):
        # Title too short (< 3 chars)
        with self.assertRaises(ValidationError):
            InsightItem(
                id="ins_short_title",
                type=InsightType.ENGAGEMENT_SURGE,
                title="AB",
                summary="Valid summary text describing something in detail.",
                confidence=0.75,
            )

        # Summary too short (< 10 chars)
        with self.assertRaises(ValidationError):
            InsightItem(
                id="ins_short_summary",
                type=InsightType.ENGAGEMENT_SURGE,
                title="Valid Headline",
                summary="Too short",
                confidence=0.75,
            )

    def test_evidence_negative_volume_validation(self):
        # Negative current volume must fail
        with self.assertRaises(ValidationError):
            InsightEvidence(current_volume=-10)

        # Negative baseline volume must fail
        with self.assertRaises(ValidationError):
            InsightEvidence(baseline_volume=-5)

    def test_serialization_roundtrip(self):
        evidence = InsightEvidence(
            topic_label="AI Ingestion",
            growth_rate=88.2,
            current_volume=45,
            platforms=["Reddit", "YouTube"],
            post_ids=[42, 43],
        )
        insight = InsightItem(
            id="ins_json_01",
            type=InsightType.CROSS_PLATFORM_PROPAGATION,
            title="Cross-platform propagation of AI tutorials",
            summary="Emergence initially detected on Reddit before video coverage on YouTube.",
            severity=InsightSeverity.MEDIUM,
            confidence=0.88,
            evidence=evidence,
        )

        json_str = insight.model_dump_json()
        data = json.loads(json_str)

        self.assertEqual(data["id"], "ins_json_01")
        self.assertEqual(data["type"], "cross_platform_propagation")
        self.assertEqual(data["severity"], "medium")
        self.assertEqual(data["evidence"]["platforms"], ["Reddit", "YouTube"])

        # Deserialize back
        reconstructed = InsightItem.model_validate(data)
        self.assertEqual(reconstructed.id, insight.id)
        self.assertEqual(reconstructed.confidence, insight.confidence)
        self.assertEqual(reconstructed.evidence.post_ids, [42, 43])

    def test_batch_insight_result_container(self):
        item1 = InsightItem(
            id="ins_b1",
            type=InsightType.EMERGING_TREND,
            title="Critical emerging issue",
            summary="Emergency alert regarding high volume surge on public feeds.",
            severity=InsightSeverity.CRITICAL,
            confidence=0.98,
        )
        item2 = InsightItem(
            id="ins_b2",
            type=InsightType.DATA_QUALITY_ALERT,
            title="Informational quality report",
            summary="Mild parsing irregularity detected on legacy Telegram feed.",
            severity=InsightSeverity.INFO,
            confidence=0.72,
        )

        batch = BatchInsightResult(
            total_insights=2,
            critical_count=1,
            info_count=1,
            insights=[item1, item2],
            model="insightx-intelligence-engine-v1",
        )

        self.assertEqual(batch.total_insights, 2)
        self.assertEqual(batch.critical_count, 1)
        self.assertEqual(batch.info_count, 1)
        self.assertEqual(batch.high_count, 0)
        self.assertEqual(len(batch.insights), 2)
        self.assertEqual(batch.model, "insightx-intelligence-engine-v1")

    def test_intelligence_analyze_request_validation(self):
        req = IntelligenceAnalyzeRequest(
            platform="X",
            min_confidence=0.6,
            max_insights=15,
        )
        self.assertEqual(req.platform, "X")
        self.assertEqual(req.min_confidence, 0.6)
        self.assertEqual(req.max_insights, 15)

        # Invalid min_confidence > 1.0
        with self.assertRaises(ValidationError):
            IntelligenceAnalyzeRequest(min_confidence=1.5)

        # Invalid max_insights < 1
        with self.assertRaises(ValidationError):
            IntelligenceAnalyzeRequest(max_insights=0)


if __name__ == "__main__":
    unittest.main()
