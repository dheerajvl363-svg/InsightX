from datetime import datetime, timezone
import unittest

from app.schemas.data_quality import AnalyticsReadyPost
from app.schemas.post import NormalizedPost, PostMetricsSchema
from app.schemas.sentiment import (
    BatchSentimentResult,
    SentimentLabel,
    SentimentProbabilities,
    SentimentResult,
)
from app.services.data_quality import DataQualityService
from app.services.sentiment import (
    BaseSentimentEngine,
    RuleBasedSentimentEngine,
    SentimentAnalysisService,
    SentimentInferenceResult,
    get_sentiment_analyzer,
)


class TestSentimentAnalysisEngine(unittest.TestCase):
    """
    Comprehensive tests for Phase 3 Component 3.2: Sentiment Analysis Engine.
    """

    def setUp(self):
        self.analyzer = SentimentAnalysisService()

    def _make_ready_post(
        self,
        text: str,
        platform: str = "X",
        external_id: str = "sent_test_001",
        post_id: int = 1,
    ) -> AnalyticsReadyPost:
        return AnalyticsReadyPost(
            id=post_id,
            platform=platform,
            external_post_id=external_id,
            text=text,
            raw_text=text,
            posted_at=datetime(2026, 9, 8, 12, 0, 0, tzinfo=timezone.utc),
            char_count=len(text),
            word_count=len(text.split()),
        )

    # 1. Positive statements
    def test_1_positive_statements(self):
        """Clearly positive statements are classified as positive with score > 0."""
        positive_texts = [
            "InsightX is an amazing and outstanding platform for AI analytics!",
            "Great job to the team! The new release is fast, reliable, and secure.",
            "I love this product, it is wonderful and truly brilliant.",
            "Excited to announce our successful breakthrough! 🚀",
        ]
        for text in positive_texts:
            post = self._make_ready_post(text)
            result = self.analyzer.analyze(post)
            self.assertEqual(result.label, SentimentLabel.POSITIVE, f"Failed for: {text}")
            self.assertGreater(result.score, 0.05)
            self.assertGreater(result.probabilities.positive, result.probabilities.negative)
            self.assertGreater(result.confidence, 0.5)
            self.assertEqual(result.post_id, 1)
            self.assertEqual(result.external_post_id, "sent_test_001")

    # 2. Negative statements
    def test_2_negative_statements(self):
        """Clearly negative statements are classified as negative with score < 0."""
        negative_texts = [
            "This service is terrible and horrible, worst experience ever.",
            "The app crashed again with tons of lag and annoying bugs. Totally broken.",
            "Very disappointed with this useless failure of an update.",
            "Beware of this scam! Horrible fraud and corrupt system. 💩",
        ]
        for text in negative_texts:
            post = self._make_ready_post(text)
            result = self.analyzer.analyze(post)
            self.assertEqual(result.label, SentimentLabel.NEGATIVE, f"Failed for: {text}")
            self.assertLess(result.score, -0.05)
            self.assertGreater(result.probabilities.negative, result.probabilities.positive)
            self.assertGreater(result.confidence, 0.5)

    # 3. Neutral statements
    def test_3_neutral_statements(self):
        """Factual, non-polarized statements are classified as neutral."""
        neutral_texts = [
            "The annual tech conference will start at 10:00 AM on Monday.",
            "InsightX processes data streams from multiple social media platforms.",
            "A software update was deployed to the staging environment.",
            "The weather forecast predicts rain in the evening.",
        ]
        for text in neutral_texts:
            post = self._make_ready_post(text)
            result = self.analyzer.analyze(post)
            self.assertEqual(result.label, SentimentLabel.NEUTRAL, f"Failed for: {text}")
            self.assertGreaterEqual(result.score, -0.05)
            self.assertLessEqual(result.score, 0.05)
            self.assertGreater(result.probabilities.neutral, result.probabilities.positive)
            self.assertGreater(result.probabilities.neutral, result.probabilities.negative)

    # 4. Negation handling
    def test_4_negation_inversion(self):
        """Negation words properly invert polarity."""
        # 'good' is positive, 'not good' is negative
        res_pos = self.analyzer.analyze_text("The service is good and reliable.")
        self.assertEqual(res_pos.label, SentimentLabel.POSITIVE)

        res_neg = self.analyzer.analyze_text("The service is not good and not reliable.")
        self.assertEqual(res_neg.label, SentimentLabel.NEGATIVE)
        self.assertLess(res_neg.score, 0.0)

        # 'never failed' is positive
        res_never_failed = self.analyzer.analyze_text("Our pipeline never failed under load.")
        self.assertGreaterEqual(res_never_failed.score, 0.0)

    # 5. Intensifiers and Diminishers
    def test_5_intensifiers_and_diminishers(self):
        """Intensifiers increase score magnitude while diminishers reduce it."""
        base_res = self.analyzer.analyze_text("The results are good.")
        boosted_res = self.analyzer.analyze_text("The results are extremely super good!")
        diminished_res = self.analyzer.analyze_text("The results are barely good.")

        self.assertGreater(boosted_res.score, base_res.score)
        self.assertLess(diminished_res.score, boosted_res.score)

    # 6. ALL CAPS and Exclamation mark emphasis
    def test_6_capitalization_and_exclamations(self):
        """ALL CAPS and multiple exclamation marks amplify polarity."""
        normal_res = self.analyzer.analyze_text("This is awesome.")
        amplified_res = self.analyzer.analyze_text("THIS IS AWESOME!!!")

        self.assertGreater(amplified_res.score, normal_res.score)
        self.assertGreater(amplified_res.details.get("exclamations", 0), 0)

    # 7. Emoji sentiment handling
    def test_7_emoji_sentiment(self):
        """Emojis carry direct positive or negative valence."""
        res_positive_emoji = self.analyzer.analyze_text("Launch day 🚀 🔥 💯")
        self.assertEqual(res_positive_emoji.label, SentimentLabel.POSITIVE)
        self.assertGreater(res_positive_emoji.score, 0.5)

        res_negative_emoji = self.analyzer.analyze_text("Broken build 😡 💩 💔")
        self.assertEqual(res_negative_emoji.label, SentimentLabel.NEGATIVE)
        self.assertLess(res_negative_emoji.score, -0.5)

    # 8. Hashtags sentiment handling
    def test_8_hashtag_sentiment(self):
        """Hashtags with sentiment words are parsed properly."""
        res_ht_pos = self.analyzer.analyze_text("Check out our new release #Awesome #Breakthrough")
        self.assertEqual(res_ht_pos.label, SentimentLabel.POSITIVE)

        res_ht_neg = self.analyzer.analyze_text("System outage #Disaster #Fail")
        self.assertEqual(res_ht_neg.label, SentimentLabel.NEGATIVE)

    # 9. Edge cases: short text, empty text, punctuation-only
    def test_9_edge_cases(self):
        """Handles short text, empty text, and symbols safely without throwing."""
        # Empty text
        res_empty = self.analyzer.analyze_text("")
        self.assertEqual(res_empty.label, SentimentLabel.NEUTRAL)
        self.assertEqual(res_empty.score, 0.0)

        # Whitespace
        res_ws = self.analyzer.analyze_text("   \n\t  ")
        self.assertEqual(res_ws.label, SentimentLabel.NEUTRAL)

        # Punctuation only
        res_punct = self.analyzer.analyze_text("... ??? ---")
        self.assertEqual(res_punct.label, SentimentLabel.NEUTRAL)

        # Single word
        res_single = self.analyzer.analyze_text("Perfect")
        self.assertEqual(res_single.label, SentimentLabel.POSITIVE)

    # 10. Type safety on analyze()
    def test_10_type_safety(self):
        """Passing non-AnalyticsReadyPost to analyze() raises TypeError."""
        with self.assertRaises(TypeError):
            self.analyzer.analyze("plain string is invalid")

        with self.assertRaises(TypeError):
            self.analyzer.analyze({"dict": "is invalid"})

    # 11. Batch sentiment analysis
    def test_11_batch_sentiment_analysis(self):
        """Batch processing correctly computes aggregate stats and itemized results."""
        posts = [
            self._make_ready_post("Amazing innovation! 🚀", external_id="p1", post_id=1),
            self._make_ready_post("Terrible disaster and worst failure.", external_id="p2", post_id=2),
            self._make_ready_post("The server updated today at noon.", external_id="p3", post_id=3),
            self._make_ready_post("Super happy with the great results!", external_id="p4", post_id=4),
        ]

        batch_result = self.analyzer.analyze_batch(posts)
        self.assertIsInstance(batch_result, BatchSentimentResult)
        self.assertEqual(batch_result.total_analyzed, 4)
        self.assertEqual(batch_result.positive_count, 2)
        self.assertEqual(batch_result.negative_count, 1)
        self.assertEqual(batch_result.neutral_count, 1)
        self.assertEqual(len(batch_result.results), 4)

        # First post is positive
        self.assertEqual(batch_result.results[0].external_post_id, "p1")
        self.assertEqual(batch_result.results[0].label, SentimentLabel.POSITIVE)

        # Second post is negative
        self.assertEqual(batch_result.results[1].external_post_id, "p2")
        self.assertEqual(batch_result.results[1].label, SentimentLabel.NEGATIVE)

        # Empty batch returns zero counts safely
        empty_batch = self.analyzer.analyze_batch([])
        self.assertEqual(empty_batch.total_analyzed, 0)
        self.assertEqual(empty_batch.average_score, 0.0)

    # 12. Swappable Custom Sentiment Engine (Mockability)
    def test_12_swappable_custom_engine(self):
        """Demonstrates dependency injection and engine swappability."""
        class MockSentimentEngine(BaseSentimentEngine):
            @property
            def model_name(self) -> str:
                return "mock-transformer-v2"

            def analyze_text(self, text: str) -> SentimentInferenceResult:
                return SentimentInferenceResult(
                    label=SentimentLabel.POSITIVE,
                    score=0.9999,
                    confidence=0.99,
                    probabilities=SentimentProbabilities(positive=0.99, neutral=0.01, negative=0.0),
                    model_name=self.model_name,
                    details={"mocked": True},
                )

        custom_service = SentimentAnalysisService(engine=MockSentimentEngine())
        post = self._make_ready_post("Any text")
        result = custom_service.analyze(post)

        self.assertEqual(result.model, "mock-transformer-v2")
        self.assertEqual(result.label, SentimentLabel.POSITIVE)
        self.assertEqual(result.score, 0.9999)
        self.assertTrue(result.details.get("mocked"))

    # 13. End-to-end integration flow from NormalizedPost
    def test_13_end_to_end_pipeline_integration(self):
        """
        Tests the full Phase 3 pipeline:
        NormalizedPost -> DataQualityService -> AnalyticsReadyPost -> SentimentAnalyzer -> SentimentResult
        """
        norm_post = NormalizedPost(
            platform_name="X",
            external_post_id="pipeline_e2e_001",
            text="InsightX platform rollout was a magnificent success! 🌟 #Innovation",
            author_username="lead_analyst",
            author_display_name="Lead Analyst",
            posted_at=datetime(2026, 9, 8, 14, 0, 0, tzinfo=timezone.utc),
            collected_at=datetime(2026, 9, 8, 14, 5, 0, tzinfo=timezone.utc),
            url="https://x.com/lead_analyst/status/pipeline_e2e_001",
            language="en",
            metrics=PostMetricsSchema(likes=250, comments=20, shares=40, views=3000),
            metadata={"source": "verified_stream"},
            raw_payload={"tweet_id": "pipeline_e2e_001"},
        )

        # 1. Quality & Analytics Input Layer
        quality_res = DataQualityService.validate_and_prepare(norm_post)
        self.assertTrue(quality_res.is_valid)
        self.assertIsNotNone(quality_res.post)

        # 2. Sentiment Analysis Engine
        sentiment_res = self.analyzer.analyze(quality_res.post)
        self.assertIsInstance(sentiment_res, SentimentResult)
        self.assertEqual(sentiment_res.external_post_id, "pipeline_e2e_001")
        self.assertEqual(sentiment_res.label, SentimentLabel.POSITIVE)
        self.assertGreater(sentiment_res.score, 0.5)
        self.assertIn("has_emojis", quality_res.post.quality_flags)
        self.assertIn("has_hashtags", quality_res.post.quality_flags)


if __name__ == "__main__":
    unittest.main()
