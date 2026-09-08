from datetime import datetime, timezone
import unittest

from app.schemas.data_quality import AnalyticsReadyPost
from app.schemas.emotion import (
    BatchEmotionResult,
    EmotionLabel,
    EmotionProbabilities,
    EmotionResult,
)
from app.schemas.post import NormalizedPost, PostMetricsSchema
from app.services.data_quality import DataQualityService
from app.services.emotion import (
    BaseEmotionEngine,
    EmotionAnalysisService,
    EmotionInferenceResult,
    RuleBasedEmotionEngine,
    get_emotion_analyzer,
)


class TestEmotionAnalysisEngine(unittest.TestCase):
    """
    Unit and integration tests for Phase 3 Component 3.3: Emotion Analysis Engine.
    """

    def setUp(self):
        self.analyzer = EmotionAnalysisService()

    def _make_ready_post(
        self,
        text: str,
        platform: str = "X",
        external_id: str = "emo_test_001",
        post_id: int = 10,
    ) -> AnalyticsReadyPost:
        return AnalyticsReadyPost(
            id=post_id,
            platform=platform,
            external_post_id=external_id,
            text=text,
            raw_text=text,
            posted_at=datetime(2026, 9, 8, 14, 0, 0, tzinfo=timezone.utc),
            char_count=len(text),
            word_count=len(text.split()),
        )

    # 1. Joy
    def test_1_joy_detection(self):
        """Celebration, happiness, excitement, and triumph are classified as joy."""
        joy_samples = [
            "We are thrilled to announce our victory in the SIH hackathon! 🏆 🥳",
            "I love this new feature so much, feeling truly blessed and happy! ❤️",
            "Congratulations to the whole team on a fantastic and wonderful launch!",
            "Enjoying this beautiful morning with great coffee and smiles! 😊",
        ]
        for text in joy_samples:
            post = self._make_ready_post(text)
            result = self.analyzer.analyze(post)
            self.assertEqual(result.primary_emotion, EmotionLabel.JOY, f"Failed for: {text}")
            self.assertGreater(result.probabilities.joy, result.probabilities.sadness)
            self.assertGreater(result.confidence, 0.4)
            self.assertEqual(result.post_id, 10)
            self.assertEqual(result.external_post_id, "emo_test_001")

    # 2. Sadness
    def test_2_sadness_detection(self):
        """Grief, heartbreak, disappointment, and sorrow are classified as sadness."""
        sadness_samples = [
            "Heartbroken and deeply saddened by the tragic loss of our colleague. 💔 😢",
            "I feel so lonely and depressed, crying all night over this failure. 😭",
            "Deeply disappointed by the canceled event, feeling down and sorrowful.",
            "Such a miserable and devastating tragedy for everyone involved.",
        ]
        for text in sadness_samples:
            post = self._make_ready_post(text)
            result = self.analyzer.analyze(post)
            self.assertEqual(result.primary_emotion, EmotionLabel.SADNESS, f"Failed for: {text}")
            self.assertGreater(result.probabilities.sadness, result.probabilities.joy)

    # 3. Anger
    def test_3_anger_detection(self):
        """Rage, outrage, fury, and extreme irritation are classified as anger."""
        anger_samples = [
            "I am furious! The corrupt service cheated and scammed us! 🤬 😡",
            "This infuriating lag and broken update is complete bullshit. So pissed!",
            "Absolute disgrace! I hate this abusive customer support with a burning rage.",
            "Ridiculous pricing policy, what an infuriating robbery and fraud!",
        ]
        for text in anger_samples:
            post = self._make_ready_post(text)
            result = self.analyzer.analyze(post)
            self.assertEqual(result.primary_emotion, EmotionLabel.ANGER, f"Failed for: {text}")
            self.assertGreater(result.probabilities.anger, result.probabilities.joy)

    # 4. Fear
    def test_4_fear_detection(self):
        """Panic, dread, anxiety, danger, and terror are classified as fear."""
        fear_samples = [
            "URGENT WARNING: Severe security vulnerability detected, dangerous threat! 🚨 ⚠️",
            "I am terrified and panicking about the server outage and data loss. 😱",
            "So anxious and scared about the impending economic crisis and risks.",
            "Horrific cyberattack threatening critical infrastructure, unsafe conditions!",
        ]
        for text in fear_samples:
            post = self._make_ready_post(text)
            result = self.analyzer.analyze(post)
            self.assertEqual(result.primary_emotion, EmotionLabel.FEAR, f"Failed for: {text}")
            self.assertGreater(result.probabilities.fear, result.probabilities.joy)

    # 5. Surprise
    def test_5_surprise_detection(self):
        """Shock, unexpected discoveries, mindblown reactions are classified as surprise."""
        surprise_samples = [
            "Whoa! Completely stunned and shocked by this unexpected announcement! 🤯",
            "Astonishing breakthrough! Mindblown by the incredible sudden speedup. ⚡",
            "Unbelievable discovery! I am speechless and astounded at these results.",
            "OMG! That was totally unforeseen and jawdropping! ‼️",
        ]
        for text in surprise_samples:
            post = self._make_ready_post(text)
            result = self.analyzer.analyze(post)
            self.assertEqual(result.primary_emotion, EmotionLabel.SURPRISE, f"Failed for: {text}")
            self.assertGreater(result.probabilities.surprise, result.probabilities.joy)

    # 6. Disgust
    def test_6_disgust_detection(self):
        """Revulsion, repulsive conditions, and cringe are classified as disgust."""
        disgust_samples = [
            "That was so gross and disgusting, feeling completely nauseated! 🤮",
            "Nasty, repulsive, and vile behavior. Totally abhorrent and toxic! 🤢",
            "Eww, what a filthy and revolting scam, absolute trash! 💩",
            "Cringey and distasteful advertisement, makes me sick.",
        ]
        for text in disgust_samples:
            post = self._make_ready_post(text)
            result = self.analyzer.analyze(post)
            self.assertEqual(result.primary_emotion, EmotionLabel.DISGUST, f"Failed for: {text}")
            self.assertGreater(result.probabilities.disgust, result.probabilities.joy)

    # 7. Neutral
    def test_7_neutral_detection(self):
        """Factual, objective, non-emotional statements are classified as neutral."""
        neutral_samples = [
            "The database migration completed at 04:00 UTC without errors.",
            "InsightX supports PostgreSQL for persistent storage and querying.",
            "The quarterly financial report was published on the investor relations portal.",
            "Meeting scheduled for 2:30 PM in conference room B.",
        ]
        for text in neutral_samples:
            post = self._make_ready_post(text)
            result = self.analyzer.analyze(post)
            self.assertEqual(result.primary_emotion, EmotionLabel.NEUTRAL, f"Failed for: {text}")
            self.assertGreater(result.probabilities.neutral, 0.35)

    # 8. Social-media signals: Emojis, Hashtags, ALL CAPS, Exclamation points
    def test_8_social_media_signals(self):
        """Social-media features (emojis, hashtags, caps, exclamations) amplify emotion signals."""
        # Emoji-only
        res_emoji_joy = self.analyzer.analyze_text("🚀 🎉 🥳 ✨")
        self.assertEqual(res_emoji_joy.primary_emotion, EmotionLabel.JOY)

        res_emoji_fear = self.analyzer.analyze_text("😱 🚨 ⚠️ 🥶")
        self.assertEqual(res_emoji_fear.primary_emotion, EmotionLabel.FEAR)

        # Hashtags
        res_ht_anger = self.analyzer.analyze_text("System failure again #Outrage #Furious")
        self.assertEqual(res_ht_anger.primary_emotion, EmotionLabel.ANGER)

        # ALL CAPS & Exclamations
        res_caps = self.analyzer.analyze_text("I AM SO FURIOUS RIGHT NOW!!!")
        self.assertEqual(res_caps.primary_emotion, EmotionLabel.ANGER)
        self.assertGreater(res_caps.probabilities.anger, 0.7)

    # 9. Contextual modifiers: Negations and Intensifiers
    def test_9_negations_and_intensifiers(self):
        """Negations dampen target emotion while intensifiers amplify it."""
        # 'happy' vs 'not happy'
        res_happy = self.analyzer.analyze_text("I am very happy with this.")
        self.assertEqual(res_happy.primary_emotion, EmotionLabel.JOY)

        res_not_happy = self.analyzer.analyze_text("I am not happy with this.")
        self.assertNotEqual(res_not_happy.primary_emotion, EmotionLabel.JOY)

        # 'terrified' vs 'not terrified'
        res_terrified = self.analyzer.analyze_text("I am extremely terrified.")
        self.assertEqual(res_terrified.primary_emotion, EmotionLabel.FEAR)

        res_not_scared = self.analyzer.analyze_text("We are not afraid and not scared.")
        self.assertNotEqual(res_not_scared.primary_emotion, EmotionLabel.FEAR)

    # 10. Edge cases: Empty text, whitespace, punctuation, short text
    def test_10_edge_cases(self):
        """Handles empty inputs and non-alphanumeric text gracefully."""
        res_empty = self.analyzer.analyze_text("")
        self.assertEqual(res_empty.primary_emotion, EmotionLabel.NEUTRAL)
        self.assertEqual(res_empty.confidence, 1.0)

        res_ws = self.analyzer.analyze_text("   \n\t ")
        self.assertEqual(res_ws.primary_emotion, EmotionLabel.NEUTRAL)

        res_punct = self.analyzer.analyze_text("... ??? ---")
        self.assertEqual(res_punct.primary_emotion, EmotionLabel.NEUTRAL)

        res_short = self.analyzer.analyze_text("Yay!")
        self.assertEqual(res_short.primary_emotion, EmotionLabel.JOY)

    # 11. Type safety on analyze()
    def test_11_type_safety(self):
        """Passing non-AnalyticsReadyPost to analyze() raises TypeError."""
        with self.assertRaises(TypeError):
            self.analyzer.analyze("invalid string")

        with self.assertRaises(TypeError):
            self.analyzer.analyze({"text": "invalid dict"})

    # 12. Batch emotion analysis
    def test_12_batch_emotion_analysis(self):
        """Batch processing correctly computes aggregated emotion distribution and itemized results."""
        posts = [
            self._make_ready_post("Thrilled with the victory! 🎉", external_id="e1", post_id=1),
            self._make_ready_post("Terrible tragedy and grief. 💔", external_id="e2", post_id=2),
            self._make_ready_post("Scammed and furious! 😡", external_id="e3", post_id=3),
            self._make_ready_post("The API returns JSON format.", external_id="e4", post_id=4),
        ]

        batch_result = self.analyzer.analyze_batch(posts)
        self.assertIsInstance(batch_result, BatchEmotionResult)
        self.assertEqual(batch_result.total_analyzed, 4)
        self.assertEqual(batch_result.emotion_distribution["joy"], 1)
        self.assertEqual(batch_result.emotion_distribution["sadness"], 1)
        self.assertEqual(batch_result.emotion_distribution["anger"], 1)
        self.assertEqual(batch_result.emotion_distribution["neutral"], 1)
        self.assertEqual(len(batch_result.results), 4)

        # Empty batch returns safe empty distribution
        empty_batch = self.analyzer.analyze_batch([])
        self.assertEqual(empty_batch.total_analyzed, 0)
        self.assertEqual(len(empty_batch.results), 0)

    # 13. Swappable Custom Emotion Engine (Mockability)
    def test_13_swappable_custom_engine(self):
        """Demonstrates dependency injection and engine swappability."""
        class MockEmotionEngine(BaseEmotionEngine):
            @property
            def model_name(self) -> str:
                return "mock-emotion-transformer-v3"

            def analyze_text(self, text: str) -> EmotionInferenceResult:
                return EmotionInferenceResult(
                    primary_emotion=EmotionLabel.JOY,
                    confidence=0.999,
                    probabilities=EmotionProbabilities(joy=0.999, neutral=0.001),
                    model_name=self.model_name,
                    details={"mocked": True},
                )

        custom_analyzer = EmotionAnalysisService(engine=MockEmotionEngine())
        post = self._make_ready_post("Any test input")
        result = custom_analyzer.analyze(post)

        self.assertEqual(result.model, "mock-emotion-transformer-v3")
        self.assertEqual(result.primary_emotion, EmotionLabel.JOY)
        self.assertEqual(result.confidence, 0.999)
        self.assertTrue(result.details.get("mocked"))

    # 14. Full End-to-End Pipeline Integration
    def test_14_end_to_end_pipeline_integration(self):
        """
        Tests the full Phase 3 pipeline:
        NormalizedPost -> DataQualityService -> AnalyticsReadyPost -> EmotionAnalysisService -> EmotionResult
        """
        norm_post = NormalizedPost(
            platform_name="X",
            external_post_id="emo_pipeline_001",
            text="Celebrating our championship triumph with the team! 🚀 🏆 #Winners",
            author_username="champ_team",
            author_display_name="Championship Team",
            posted_at=datetime(2026, 9, 8, 16, 0, 0, tzinfo=timezone.utc),
            collected_at=datetime(2026, 9, 8, 16, 2, 0, tzinfo=timezone.utc),
            url="https://x.com/champ_team/status/emo_pipeline_001",
            language="en",
            metrics=PostMetricsSchema(likes=1200, comments=85, shares=210, views=18000),
            metadata={"verified": True},
            raw_payload={"id": "emo_pipeline_001"},
        )

        # 1. Quality & Analytics Input Layer
        quality_res = DataQualityService.validate_and_prepare(norm_post)
        self.assertTrue(quality_res.is_valid)
        self.assertIsNotNone(quality_res.post)

        # 2. Emotion Analysis Engine
        emotion_res = self.analyzer.analyze(quality_res.post)
        self.assertIsInstance(emotion_res, EmotionResult)
        self.assertEqual(emotion_res.external_post_id, "emo_pipeline_001")
        self.assertEqual(emotion_res.primary_emotion, EmotionLabel.JOY)
        self.assertGreater(emotion_res.probabilities.joy, 0.7)
        self.assertGreater(emotion_res.confidence, 0.7)


if __name__ == "__main__":
    unittest.main()
