from datetime import datetime, timezone
import unittest

from app.schemas.data_quality import AnalyticsReadyPost
from app.schemas.post import NormalizedPost, PostMetricsSchema
from app.schemas.topic import (
    BatchTopicResult,
    ExtractedTopic,
    SinglePostTopicResult,
)
from app.services.data_quality import DataQualityService
from app.services.emotion import EmotionAnalysisService
from app.services.sentiment import SentimentAnalysisService
from app.services.topic import (
    BaseTopicEngine,
    RuleBasedTopicEngine,
    TopicAnalysisService,
    get_topic_analyzer,
)


class TestTopicExtractionEngine(unittest.TestCase):
    """
    Unit and integration tests for Phase 3 Component 3.4: Topic Extraction & Narrative Detection.
    """

    def setUp(self):
        self.analyzer = TopicAnalysisService()

    def _make_ready_post(
        self,
        text: str,
        platform: str = "X",
        external_id: str = "top_test_001",
        post_id: int = 100,
    ) -> AnalyticsReadyPost:
        return AnalyticsReadyPost(
            id=post_id,
            platform=platform,
            external_post_id=external_id,
            text=text,
            raw_text=text,
            posted_at=datetime(2026, 9, 8, 15, 0, 0, tzinfo=timezone.utc),
            char_count=len(text),
            word_count=len(text.split()),
        )

    # 1. Single-post keyword extraction & stopword removal
    def test_1_single_post_keyword_extraction(self):
        """Extracts meaningful keywords while removing common stopwords and punctuation."""
        text = "The new Hyderabad metro fares increased significantly today due to inflation. #HyderabadMetro #Transit"
        post = self._make_ready_post(text, external_id="p1", post_id=1)

        result = self.analyzer.extract_post_topics(post)
        self.assertIsInstance(result, SinglePostTopicResult)
        self.assertEqual(result.post_id, 1)
        self.assertEqual(result.external_post_id, "p1")

        # Check that stopwords like 'the', 'due', 'to' are filtered out
        self.assertNotIn("the", result.keywords)
        self.assertNotIn("due", result.keywords)
        self.assertNotIn("to", result.keywords)

        # Check meaningful keywords
        self.assertIn("hyderabad", result.keywords)
        self.assertIn("metro", result.keywords)
        self.assertIn("fares", result.keywords)
        self.assertIn("hyderabadmetro", result.hashtags)
        self.assertIn("transit", result.hashtags)

    # 2. Multi-word phrase extraction
    def test_2_phrase_extraction(self):
        """Extracts multi-word candidate phrases (bigrams/trigrams)."""
        text = "Artificial intelligence and machine learning pipelines are driving automated data analytics."
        post = self._make_ready_post(text)

        result = self.analyzer.extract_post_topics(post)
        self.assertTrue(any("artificial intelligence" in p for p in result.keyphrases))
        self.assertTrue(any("machine learning" in p for p in result.keyphrases))
        self.assertIsNotNone(result.suggested_label)

    # 3. Multi-post topic clustering
    def test_3_multi_post_topic_clustering(self):
        """Clusters related posts together into cohesive topic groups."""
        posts = [
            # Topic A: Metro Fares (3 posts)
            self._make_ready_post("Hyderabad metro fares increased again.", external_id="m1", post_id=1),
            self._make_ready_post("Metro ticket prices are becoming very expensive.", external_id="m2", post_id=2),
            self._make_ready_post("Why did the Hyderabad metro increase ticket prices? #HyderabadMetro", external_id="m3", post_id=3),

            # Topic B: AI Hackathon (2 posts)
            self._make_ready_post("SIH 2026 hackathon registration is now open! #SIH2026", external_id="h1", post_id=4),
            self._make_ready_post("Excited to build our AI project for the SIH hackathon! #SIH2026", external_id="h2", post_id=5),
        ]

        batch_result = self.analyzer.extract_topics(posts)
        self.assertIsInstance(batch_result, BatchTopicResult)
        self.assertEqual(batch_result.total_posts_analyzed, 5)
        self.assertEqual(batch_result.total_topics_found, 2)

        # Check that the two largest topic clusters exist
        topic_labels = [t.label.lower() for t in batch_result.topics]
        self.assertTrue(any("metro" in l for l in topic_labels))
        self.assertTrue(any("sih" in l or "hackathon" in l for l in topic_labels))

        # Check post counts
        counts = [t.post_count for t in batch_result.topics]
        self.assertEqual(counts, [3, 2])

        # Check that post IDs were grouped properly
        metro_topic = next(t for t in batch_result.topics if "metro" in t.label.lower())
        self.assertEqual(len(metro_topic.post_ids), 3)
        self.assertIn(1, metro_topic.post_ids)
        self.assertIn(2, metro_topic.post_ids)
        self.assertIn(3, metro_topic.post_ids)

    # 4. Single post in batch
    def test_4_single_post_batch(self):
        """Batch of one post creates a single topic cluster."""
        post = self._make_ready_post("Quantum computing advances rapidly in research labs.", external_id="q1", post_id=99)
        batch_result = self.analyzer.extract_topics([post])

        self.assertEqual(batch_result.total_posts_analyzed, 1)
        self.assertEqual(batch_result.total_topics_found, 1)
        topic = batch_result.topics[0]
        self.assertEqual(topic.post_count, 1)
        self.assertIn(99, topic.post_ids)
        self.assertTrue(any("quantum" in k for k in topic.keywords))

    # 5. Empty batch
    def test_5_empty_batch(self):
        """Empty batch returns clean zero-count result without error."""
        batch_result = self.analyzer.extract_topics([])
        self.assertEqual(batch_result.total_posts_analyzed, 0)
        self.assertEqual(batch_result.total_topics_found, 0)
        self.assertEqual(len(batch_result.topics), 0)

    # 6. Stopwords-only and punctuation-only text
    def test_6_noise_and_stopwords_handling(self):
        """Posts containing only stopwords or punctuation produce clean fallback without crashing."""
        post_stops = self._make_ready_post("it is what it is and that is that", external_id="stop1")
        res1 = self.analyzer.extract_post_topics(post_stops)
        self.assertEqual(len(res1.keywords), 0)

        post_punct = self._make_ready_post("... ??? !!! ---", external_id="punc1")
        res2 = self.analyzer.extract_post_topics(post_punct)
        self.assertEqual(len(res2.keywords), 0)

    # 7. Hashtag extraction and preservation
    def test_7_hashtag_extraction(self):
        """Hashtags are cleanly extracted and incorporated into topic keywords."""
        post = self._make_ready_post("Breakthrough in clean energy! #RenewableEnergy #SolarPower", external_id="e1")
        result = self.analyzer.extract_post_topics(post)

        self.assertIn("renewableenergy", result.hashtags)
        self.assertIn("solarpower", result.hashtags)
        self.assertIn("renewableenergy", result.keywords)

    # 8. Deterministic extraction
    def test_8_determinism(self):
        """Identical inputs produce identical topic outputs."""
        posts = [
            self._make_ready_post("Electric vehicle sales surge across the nation. #EV"),
            self._make_ready_post("New battery technology boosts electric vehicle range."),
        ]
        res1 = self.analyzer.extract_topics(posts)
        res2 = self.analyzer.extract_topics(posts)

        self.assertEqual(res1.total_topics_found, res2.total_topics_found)
        self.assertEqual(res1.topics[0].label, res2.topics[0].label)
        self.assertEqual(res1.topics[0].keywords, res2.topics[0].keywords)
        self.assertEqual(res1.topics[0].post_count, res2.topics[0].post_count)

    # 9. Type safety
    def test_9_type_safety(self):
        """Passing non-AnalyticsReadyPost raises TypeError."""
        with self.assertRaises(TypeError):
            self.analyzer.extract_post_topics("invalid string")

        with self.assertRaises(TypeError):
            self.analyzer.extract_topics(["invalid", "list"])

    # 10. Swappable Custom Topic Engine (Mockability)
    def test_10_swappable_custom_engine(self):
        """Demonstrates dependency injection and engine swappability."""
        class MockTopicEngine(BaseTopicEngine):
            @property
            def model_name(self) -> str:
                return "mock-bertopic-v2"

            def extract_post_topics(self, post: AnalyticsReadyPost) -> SinglePostTopicResult:
                return SinglePostTopicResult(
                    post_id=post.id,
                    external_post_id=post.external_post_id,
                    keywords=["mock_keyword"],
                    keyphrases=["mock phrase"],
                    suggested_label="Mock Topic",
                )

            def extract_batch_topics(self, posts):
                return [
                    ExtractedTopic(
                        topic_id="topic_mock_ai",
                        label="Mock AI Narrative",
                        keywords=["mock", "ai"],
                        keyphrases=["mock ai"],
                        post_count=len(posts),
                        post_ids=[p.id for p in posts if p.id is not None],
                        external_post_ids=[p.external_post_id for p in posts if p.external_post_id],
                        confidence=0.95,
                    )
                ]

        custom_analyzer = TopicAnalysisService(engine=MockTopicEngine())
        posts = [self._make_ready_post("Test post 1", post_id=10), self._make_ready_post("Test post 2", post_id=20)]
        batch_res = custom_analyzer.extract_topics(posts)

        self.assertEqual(batch_res.model, "mock-bertopic-v2")
        self.assertEqual(batch_res.total_topics_found, 1)
        self.assertEqual(batch_res.topics[0].label, "Mock AI Narrative")
        self.assertEqual(batch_res.topics[0].post_ids, [10, 20])

    # 11. End-to-End Pipeline Integration with Sentiment and Emotion
    def test_11_end_to_end_pipeline_and_cross_analytics(self):
        """
        Tests the complete Phase 3 pipeline:
        NormalizedPost -> DataQualityService -> AnalyticsReadyPost -> TopicAnalysisService
        and verifies cross-analytics correlation with Sentiment and Emotion engines.
        """
        raw_posts = [
            NormalizedPost(
                platform_name="X",
                external_post_id="p_metro_1",
                text="Hyderabad metro ticket fares increased again, so furious! 😡 #HyderabadMetro",
                posted_at=datetime(2026, 9, 8, 16, 0, 0, tzinfo=timezone.utc),
                collected_at=datetime(2026, 9, 8, 16, 5, 0, tzinfo=timezone.utc),
            ),
            NormalizedPost(
                platform_name="X",
                external_post_id="p_metro_2",
                text="The new metro fares hike is totally unfair and expensive. #HyderabadMetro",
                posted_at=datetime(2026, 9, 8, 16, 10, 0, tzinfo=timezone.utc),
                collected_at=datetime(2026, 9, 8, 16, 15, 0, tzinfo=timezone.utc),
            ),
            NormalizedPost(
                platform_name="Telegram",
                external_post_id="p_hackathon_1",
                text="Thrilled to win first prize at the national AI hackathon! 🏆 🚀 #Innovation",
                posted_at=datetime(2026, 9, 8, 16, 20, 0, tzinfo=timezone.utc),
                collected_at=datetime(2026, 9, 8, 16, 25, 0, tzinfo=timezone.utc),
            ),
        ]

        # 1. Quality Layer (Component 3.1)
        quality_batch = DataQualityService.validate_batch(raw_posts)
        self.assertEqual(quality_batch.valid_count, 3)
        analytics_posts = quality_batch.valid_posts

        # 2. Topic Layer (Component 3.4)
        topic_batch = self.analyzer.extract_topics(analytics_posts)
        self.assertEqual(topic_batch.total_topics_found, 2)

        # 3. Sentiment & Emotion Analysis (Components 3.2 & 3.3)
        sentiment_analyzer = SentimentAnalysisService()
        emotion_analyzer = EmotionAnalysisService()

        metro_topic = next(t for t in topic_batch.topics if "metro" in t.label.lower())
        metro_posts = [p for p in analytics_posts if p.external_post_id in metro_topic.external_post_ids]

        metro_sentiments = [sentiment_analyzer.analyze(p) for p in metro_posts]
        metro_emotions = [emotion_analyzer.analyze(p) for p in metro_posts]

        # All metro fare increase posts are negative sentiment and angry/disgusted emotion
        self.assertTrue(all(s.label.value == "negative" for s in metro_sentiments))
        self.assertTrue(any(e.primary_emotion.value in ("anger", "disgust") for e in metro_emotions))


if __name__ == "__main__":
    unittest.main()
