from datetime import datetime, timedelta, timezone
import unittest

from app.schemas.intelligence import (
    BatchInsightResult,
    InsightEvidence,
    InsightExplanation,
    InsightItem,
    InsightSeverity,
    InsightStatus,
    InsightType,
)
from app.schemas.trend import TimeWindow
from app.services.intelligence.explanation.engine import (
    DeterministicExplanationEngine,
    get_explanation_engine,
)


class TestPhase7ExplanationEngine(unittest.TestCase):
    """
    Comprehensive test suite for Phase 7.2.3 Evidence & Explanation Layer.
    """

    def setUp(self):
        self.engine = DeterministicExplanationEngine()
        self.now = datetime.now(timezone.utc)
        self.window = TimeWindow(
            start=self.now - timedelta(hours=3),
            end=self.now,
        )

    # 1. Emerging-trend explanation
    def test_emerging_trend_explanation(self):
        evidence = InsightEvidence(
            topic_id="top_emerge_01",
            topic_label="Renewable Grid Storage",
            growth_rate=125.0,
            current_volume=30,
            baseline_volume=12,
            z_score=1.9,
            platforms=["X", "Reddit"],
            post_ids=[101, 102, 103],
            external_post_ids=["x_01", "rd_01"],
            time_window=self.window,
        )
        insight = InsightItem(
            id="ins_emerging_trend_renewable_grid_storage_123",
            type=InsightType.EMERGING_TREND,
            title="Emerging Narrative Signal: Renewable Grid Storage",
            summary="Topic 'Renewable Grid Storage' is demonstrating positive growth of 125.0% in the current window.",
            severity=InsightSeverity.HIGH,
            confidence=0.88,
            affected_topic="Renewable Grid Storage",
            affected_platforms=["X", "Reddit"],
            evidence=evidence,
            recommended_action="Inspect supporting evidence posts in Posts Explorer to track narrative origin.",
            action_items=["Review recent posts driving the topic's growth."],
        )

        exp = self.engine.explain_insight(insight)
        self.assertEqual(exp.insight_id, insight.id)
        self.assertEqual(exp.type, InsightType.EMERGING_TREND)
        self.assertEqual(exp.severity, InsightSeverity.HIGH)
        self.assertEqual(exp.confidence, 0.88)
        self.assertIn("Renewable Grid Storage", exp.interpretation)
        self.assertGreaterEqual(len(exp.facts), 3)

        # Verify factual volume statement
        volume_fact = next((f for f in exp.facts if "30 posts compared with a baseline of 12" in f), None)
        self.assertIsNotNone(volume_fact)
        self.assertIn("+125.0% growth", volume_fact)

        # Verify platform fact
        platform_fact = next((f for f in exp.facts if "X, Reddit" in f), None)
        self.assertIsNotNone(platform_fact)

        # Verify traceability
        self.assertEqual(exp.evidence_references.post_ids, [101, 102, 103])
        self.assertEqual(exp.evidence_references.external_post_ids, ["x_01", "rd_01"])

    # 2. Anomalous-spike explanation
    def test_anomalous_spike_explanation(self):
        evidence = InsightEvidence(
            topic_id="top_spike_01",
            topic_label="Flash Network Outage",
            growth_rate=650.0,
            current_volume=80,
            baseline_volume=8,
            z_score=4.25,
            platforms=["Telegram", "X"],
            post_ids=[201, 202, 203],
        )
        insight = InsightItem(
            id="ins_anomalous_spike_flash_network_outage_456",
            type=InsightType.ANOMALOUS_SPIKE,
            title="Statistical Activity Spike: Flash Network Outage",
            summary="Unusual statistical volume spike detected for 'Flash Network Outage' (z-score: 4.25).",
            severity=InsightSeverity.CRITICAL,
            confidence=0.96,
            affected_topic="Flash Network Outage",
            evidence=evidence,
            recommended_action="Verify if spike is driven by coordinated posting or a breaking event.",
        )

        exp = self.engine.explain_insight(insight)
        self.assertEqual(exp.severity, InsightSeverity.CRITICAL)
        self.assertIn("CRITICAL", exp.severity_rationale)
        self.assertIn("4.25 standard deviations", exp.facts[0])
        self.assertIn("Flash Network Outage", exp.interpretation)

    # 3. Sentiment-shift explanation
    def test_sentiment_shift_explanation(self):
        evidence = InsightEvidence(
            dominant_sentiment="negative",
            sentiment_score=-0.62,
            current_volume=50,
            raw_signals={
                "positive_count": 5,
                "negative_count": 35,
                "neutral_count": 10,
                "total_analyzed": 50,
            },
        )
        insight = InsightItem(
            id="ins_sentiment_shift_negative_789",
            type=InsightType.SENTIMENT_SHIFT,
            title="Pronounced Sentiment Concentration: Negative Tone",
            summary="Dataset shows strong negative sentiment concentration (35/50 posts).",
            severity=InsightSeverity.HIGH,
            confidence=0.85,
            evidence=evidence,
            recommended_action="Inspect driver keywords in Emotion & Sentiment radar.",
        )

        exp = self.engine.explain_insight(insight)
        self.assertEqual(exp.type, InsightType.SENTIMENT_SHIFT)
        self.assertIn("negative polarity", exp.facts[0].lower())
        self.assertIn("35 negative (70.0%)", exp.facts[1])
        self.assertIn("negative polarity concentration", exp.interpretation.lower())

    # 4. Cross-platform narrative explanation
    def test_cross_platform_explanation(self):
        evidence = InsightEvidence(
            topic_label="Global Climate Accord",
            current_volume=45,
            platforms=["X", "Reddit", "Telegram", "YouTube"],
            post_ids=[301, 302, 303, 304],
        )
        insight = InsightItem(
            id="ins_cross_platform_climate_001",
            type=InsightType.CROSS_PLATFORM_PROPAGATION,
            title="Cross-Platform Propagation: Global Climate Accord",
            summary="Narrative 'Global Climate Accord' has active discussion across 4 platforms.",
            severity=InsightSeverity.HIGH,
            confidence=0.92,
            affected_topic="Global Climate Accord",
            affected_platforms=["X", "Reddit", "Telegram", "YouTube"],
            evidence=evidence,
        )

        exp = self.engine.explain_insight(insight)
        self.assertEqual(exp.type, InsightType.CROSS_PLATFORM_PROPAGATION)
        self.assertIn("4 distinct platforms", exp.facts[0])
        self.assertIn("45 aggregate posts", exp.facts[1])
        self.assertIn("not isolated to an insular community", exp.interpretation)

    # 5. Absent metrics are cleanly omitted
    def test_absent_metrics_omitted(self):
        sparse_evidence = InsightEvidence(
            current_volume=15,
            # No baseline_volume, no growth_rate, no z_score, no platforms
        )
        insight = InsightItem(
            id="ins_sparse_01",
            type=InsightType.EMERGING_TREND,
            title="Sparse Trend",
            summary="Sparse summary text describing the signal.",
            confidence=0.65,
            evidence=sparse_evidence,
        )

        exp = self.engine.explain_insight(insight)
        # Verify no "None" string or fabricated growth rate in facts
        for fact in exp.facts:
            self.assertNotIn("None", fact)
            self.assertNotIn("unknown", fact.lower())
        self.assertEqual(len(exp.facts), 1)
        self.assertIn("15 posts in the observation window", exp.facts[0])

    # 6. Post IDs and External Post IDs remain traceable
    def test_traceability_preservation(self):
        evidence = InsightEvidence(
            topic_id="top_trace_01",
            topic_label="Traceable Topic",
            post_ids=[1001, 1002, 1003],
            external_post_ids=["ext_x_01", "ext_tg_02"],
            platforms=["X", "Telegram"],
        )
        insight = InsightItem(
            id="ins_trace_01",
            type=InsightType.EMERGING_TREND,
            title="Traceable Headline",
            summary="Detailed summary for traceability verification.",
            confidence=0.75,
            evidence=evidence,
        )

        exp = self.engine.explain_insight(insight)
        self.assertEqual(exp.evidence_references.post_ids, [1001, 1002, 1003])
        self.assertEqual(exp.evidence_references.external_post_ids, ["ext_x_01", "ext_tg_02"])
        self.assertEqual(exp.evidence_references.platforms, ["X", "Telegram"])

    # 7. Confidence & Severity rationales are explainable and preserved
    def test_confidence_and_severity_preservation(self):
        evidence = InsightEvidence(
            current_volume=50,
            z_score=3.1,
            growth_rate=200.0,
            platforms=["X", "Reddit"],
        )
        insight = InsightItem(
            id="ins_conf_01",
            type=InsightType.ANOMALOUS_SPIKE,
            title="High Confidence Spike",
            summary="Summary text describing high confidence activity.",
            severity=InsightSeverity.HIGH,
            confidence=0.91,
            evidence=evidence,
        )

        exp = self.engine.explain_insight(insight)
        self.assertEqual(exp.confidence, 0.91)
        self.assertIn("Confidence of 91%", exp.confidence_rationale)
        self.assertIn("50 recorded posts", exp.confidence_rationale)
        self.assertIn("z-score of 3.10", exp.confidence_rationale)
        self.assertIn("HIGH", exp.severity_rationale)

    # 8. Deterministic output
    def test_deterministic_output(self):
        evidence = InsightEvidence(
            current_volume=20,
            growth_rate=80.0,
            baseline_volume=10,
        )
        insight = InsightItem(
            id="ins_det_01",
            type=InsightType.EMERGING_TREND,
            title="Deterministic Title",
            summary="Deterministic summary text for testing.",
            confidence=0.80,
            evidence=evidence,
        )

        exp1 = self.engine.explain_insight(insight)
        exp2 = self.engine.explain_insight(insight)

        self.assertEqual(exp1.facts, exp2.facts)
        self.assertEqual(exp1.interpretation, exp2.interpretation)
        self.assertEqual(exp1.confidence_rationale, exp2.confidence_rationale)
        self.assertEqual(exp1.severity_rationale, exp2.severity_rationale)

    # 9. Empty evidence handling
    def test_empty_evidence_handling(self):
        empty_evidence = InsightEvidence()
        insight = InsightItem(
            id="ins_empty_ev",
            type=InsightType.DATA_QUALITY_ALERT,
            title="Quality Alert Headline",
            summary="Summary describing an alert with minimal evidence.",
            confidence=0.70,
            evidence=empty_evidence,
        )

        exp = self.engine.explain_insight(insight)
        self.assertIsInstance(exp, InsightExplanation)
        self.assertGreaterEqual(len(exp.facts), 1)
        self.assertNotIn("None", exp.facts[0])

    # 10. No unsupported claims in interpretations
    def test_no_unsupported_claims_language_check(self):
        unsupported_keywords = ["viral", "hysteria", "malicious", "disinformation", "bot-driven", "dangerous"]

        for itype in [InsightType.EMERGING_TREND, InsightType.ANOMALOUS_SPIKE, InsightType.SENTIMENT_SHIFT, InsightType.CROSS_PLATFORM_PROPAGATION]:
            insight = InsightItem(
                id=f"ins_test_{itype.value}",
                type=itype,
                title=f"Testing {itype.value}",
                summary="Summary describing testing parameters.",
                confidence=0.85,
                evidence=InsightEvidence(current_volume=20, growth_rate=50.0, z_score=2.2, platforms=["X"]),
            )
            exp = self.engine.explain_insight(insight)
            for word in unsupported_keywords:
                self.assertNotIn(word, exp.interpretation.lower())

    # 11. Batch explanation processing
    def test_batch_explanation_processing(self):
        item1 = InsightItem(
            id="ins_b_01",
            type=InsightType.EMERGING_TREND,
            title="Emerging Trend 1",
            summary="Summary for item 1 in batch.",
            confidence=0.82,
            evidence=InsightEvidence(current_volume=25, growth_rate=110.0),
        )
        item2 = InsightItem(
            id="ins_b_02",
            type=InsightType.ANOMALOUS_SPIKE,
            title="Anomalous Spike 2",
            summary="Summary for item 2 in batch.",
            confidence=0.94,
            evidence=InsightEvidence(current_volume=60, z_score=3.5),
        )

        batch_exp = self.engine.explain_batch([item1, item2])
        self.assertEqual(batch_exp.total_explanations, 2)
        self.assertEqual(len(batch_exp.explanations), 2)
        self.assertEqual(batch_exp.explanations[0].insight_id, "ins_b_01")
        self.assertEqual(batch_exp.explanations[1].insight_id, "ins_b_02")
        self.assertEqual(batch_exp.model, "insightx-explanation-deterministic-v1")

    # 12. Explanation singleton provider
    def test_explanation_engine_singleton_provider(self):
        engine = get_explanation_engine()
        self.assertIsInstance(engine, DeterministicExplanationEngine)
        self.assertEqual(engine.model_name, "insightx-explanation-deterministic-v1")


if __name__ == "__main__":
    unittest.main()
