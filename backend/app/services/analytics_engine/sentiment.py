from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.schemas.analytics_engine import (
    DetailedSentimentReport,
    IntervalUnit,
    PlatformSentimentSummary,
    PostSentimentProfile,
    SentimentDistributionSummary,
    TemporalSentimentPoint,
)
from app.services.analytics_engine.base import BaseSentimentAnalyticsEngine
from app.services.analytics_engine.engagement import extract_post_id_safe
from app.services.analytics_engine.time_series import (
    extract_post_timestamp,
    floor_to_interval,
    interval_timedelta,
)
from app.services.sentiment.base import BaseSentimentEngine
from app.services.sentiment.engine import RuleBasedSentimentEngine


def extract_post_text(post: Any) -> Tuple[str, str, str]:
    """
    Extract (text, platform, post_id) safely across multiple representation formats.
    Handles dict, AnalyticsReadyPost, NormalizedPost, PostSummary, Post ORM, or raw strings.
    """
    if isinstance(post, str):
        return post, "unknown", "text_0"

    text = ""
    platform = "unknown"
    post_id = "post_0"

    if isinstance(post, dict):
        text = str(post.get("text") or post.get("content") or post.get("caption") or "")
        platform = str(post.get("platform") or "unknown").lower()
        post_id = str(post.get("id") or post.get("external_post_id") or post.get("external_id") or "post_0")
    else:
        text = str(
            getattr(post, "text", None)
            or getattr(post, "content", None)
            or getattr(post, "caption", None)
            or ""
        )
        platform = str(getattr(post, "platform", "unknown") or "unknown").lower()
        post_id = str(
            getattr(post, "id", None)
            or getattr(post, "external_post_id", None)
            or getattr(post, "external_id", None)
            or "post_0"
        )

    return text, platform, post_id


class SentimentAnalyticsEngine(BaseSentimentAnalyticsEngine):
    """
    Modular Sentiment Analytics Engine for Phase 4.3.
    Provides per-post polarity scoring, aggregated sentiment distributions,
    platform-level breakdowns, and temporal net-sentiment trajectories.
    """

    def __init__(self, nlp_engine: Optional[BaseSentimentEngine] = None) -> None:
        self.nlp_engine = nlp_engine or RuleBasedSentimentEngine()

    def analyze_post(self, post: Any, index: int = 0) -> PostSentimentProfile:
        """Analyze polarity, sentiment label, and confidence for an individual post."""
        text, platform, post_id = extract_post_text(post)
        if not text.strip():
            # Return baseline neutral scorecard for empty/missing text
            return PostSentimentProfile(
                post_id=post_id if post_id != "post_0" else f"post_{index}",
                platform=platform,
                text_snippet=None,
                label="neutral",
                score=0.0,
                confidence=0.0,
                details={"reason": "empty_or_missing_text"},
            )

        inference = self.nlp_engine.analyze_text(text)
        snippet = text[:100] + "..." if len(text) > 100 else text

        return PostSentimentProfile(
            post_id=post_id if post_id != "post_0" else f"post_{index}",
            platform=platform,
            text_snippet=snippet,
            label=inference.label.value if hasattr(inference.label, "value") else str(inference.label),
            score=round(inference.score, 4),
            confidence=round(inference.confidence, 4),
            details=inference.details,
        )

    def analyze_batch(self, posts: List[Any]) -> List[PostSentimentProfile]:
        """Analyze a collection of posts and produce itemized sentiment profiles."""
        if not posts:
            return []
        return [self.analyze_post(post, idx) for idx, post in enumerate(posts)]

    def calculate_distribution(self, posts: List[Any]) -> SentimentDistributionSummary:
        """Calculate aggregated sentiment distribution metrics across posts."""
        if not posts:
            return SentimentDistributionSummary(
                total_evaluated=0,
                positive_count=0,
                neutral_count=0,
                negative_count=0,
                positive_percentage=0.0,
                neutral_percentage=0.0,
                negative_percentage=0.0,
                average_polarity=0.0,
                net_sentiment_score=0.0,
                dominant_sentiment="neutral",
            )

        profiles = self.analyze_batch(posts)
        total = len(profiles)
        pos_count = sum(1 for p in profiles if p.label == "positive")
        neu_count = sum(1 for p in profiles if p.label == "neutral")
        neg_count = sum(1 for p in profiles if p.label == "negative")

        pos_pct = round((pos_count / total) * 100.0, 2)
        neu_pct = round((neu_count / total) * 100.0, 2)
        neg_pct = round((neg_count / total) * 100.0, 2)

        avg_pol = round(sum(p.score for p in profiles) / total, 4)
        net_score = round((pos_count - neg_count) / total, 4)

        if pos_count > neg_count and pos_count >= neu_count:
            dominant = "positive"
        elif neg_count > pos_count and neg_count >= neu_count:
            dominant = "negative"
        else:
            dominant = "neutral"

        return SentimentDistributionSummary(
            total_evaluated=total,
            positive_count=pos_count,
            neutral_count=neu_count,
            negative_count=neg_count,
            positive_percentage=pos_pct,
            neutral_percentage=neu_pct,
            negative_percentage=neg_pct,
            average_polarity=avg_pol,
            net_sentiment_score=net_score,
            dominant_sentiment=dominant,
        )

    def calculate_platform_sentiment(self, posts: List[Any]) -> Dict[str, PlatformSentimentSummary]:
        """Calculate sentiment distribution partitioned by social media platform."""
        if not posts:
            return {}

        platform_groups: Dict[str, List[Any]] = defaultdict(list)
        for post in posts:
            _, platform, _ = extract_post_text(post)
            platform_groups[platform].append(post)

        summaries: Dict[str, PlatformSentimentSummary] = {}
        for platform_name, plat_posts in sorted(platform_groups.items()):
            dist = self.calculate_distribution(plat_posts)
            summaries[platform_name] = PlatformSentimentSummary(
                platform=platform_name,
                distribution=dist,
                dominant_sentiment=dist.dominant_sentiment,
                net_sentiment_score=dist.net_sentiment_score,
            )

        return summaries

    def calculate_temporal_sentiment(
        self, posts: List[Any], interval_unit: IntervalUnit = IntervalUnit.HOUR
    ) -> List[TemporalSentimentPoint]:
        """Calculate continuous time-series net sentiment points across temporal buckets."""
        if not posts:
            return []

        # Extract timestamps
        valid_items: List[Tuple[datetime, Any]] = []
        for post in posts:
            ts = extract_post_timestamp(post)
            if ts:
                valid_items.append((ts, post))

        if not valid_items:
            return []

        timestamps = [item[0] for item in valid_items]
        min_ts = min(timestamps)
        max_ts = max(timestamps)

        report_start = floor_to_interval(min_ts, interval_unit)
        report_end_floor = floor_to_interval(max_ts, interval_unit)
        step = interval_timedelta(interval_unit)

        bucket_boundaries: List[datetime] = []
        curr = report_start
        while curr <= report_end_floor:
            bucket_boundaries.append(curr)
            curr += step

        if not bucket_boundaries:
            bucket_boundaries = [report_start]

        bucket_posts: Dict[datetime, List[Any]] = {b: [] for b in bucket_boundaries}
        for ts, post in valid_items:
            b_start = floor_to_interval(ts, interval_unit)
            if b_start in bucket_posts:
                bucket_posts[b_start].append(post)
            elif b_start < bucket_boundaries[0]:
                bucket_posts[bucket_boundaries[0]].append(post)
            elif b_start > bucket_boundaries[-1]:
                bucket_posts[bucket_boundaries[-1]].append(post)

        temporal_points: List[TemporalSentimentPoint] = []
        for b_start in bucket_boundaries:
            b_end = b_start + step
            b_items = bucket_posts[b_start]
            if not b_items:
                temporal_points.append(
                    TemporalSentimentPoint(
                        interval_start=b_start,
                        interval_end=b_end,
                        post_count=0,
                        positive_count=0,
                        neutral_count=0,
                        negative_count=0,
                        average_polarity=0.0,
                        net_sentiment=0.0,
                        dominant_sentiment="neutral",
                    )
                )
            else:
                dist = self.calculate_distribution(b_items)
                temporal_points.append(
                    TemporalSentimentPoint(
                        interval_start=b_start,
                        interval_end=b_end,
                        post_count=dist.total_evaluated,
                        positive_count=dist.positive_count,
                        neutral_count=dist.neutral_count,
                        negative_count=dist.negative_count,
                        average_polarity=dist.average_polarity,
                        net_sentiment=dist.net_sentiment_score,
                        dominant_sentiment=dist.dominant_sentiment,
                    )
                )

        return temporal_points

    def extract_extreme_posts(
        self, posts: List[Any], limit: int = 5
    ) -> Tuple[List[PostSentimentProfile], List[PostSentimentProfile]]:
        """Extract top positive and top negative posts."""
        if not posts:
            return [], []

        profiles = self.analyze_batch(posts)
        positive_posts = [p for p in profiles if p.score > 0.0]
        negative_posts = [p for p in profiles if p.score < 0.0]

        positive_posts.sort(key=lambda p: p.score, reverse=True)
        negative_posts.sort(key=lambda p: p.score)

        return positive_posts[:limit], negative_posts[:limit]

    def generate_detailed_report(
        self, posts: List[Any], top_limit: int = 5, interval_unit: IntervalUnit = IntervalUnit.HOUR
    ) -> DetailedSentimentReport:
        """Generate comprehensive Phase 4.3 sentiment analytics report."""
        overall_dist = self.calculate_distribution(posts)
        platform_sentiment = self.calculate_platform_sentiment(posts)
        temporal_sentiment = self.calculate_temporal_sentiment(posts, interval_unit=interval_unit)
        top_pos, top_neg = self.extract_extreme_posts(posts, limit=top_limit)

        model_name = getattr(self.nlp_engine, "model_name", "RuleBasedSentimentEngine-v1.0")

        return DetailedSentimentReport(
            overall_distribution=overall_dist,
            platform_sentiment=platform_sentiment,
            temporal_sentiment=temporal_sentiment,
            top_positive_posts=top_pos,
            top_negative_posts=top_neg,
            model_metadata={
                "engine": model_name,
                "type": "lexicon_and_rule_based_valence_analyzer",
                "framework": "standard_library_deterministic",
                "capabilities": [
                    "valence_polarity_scoring",
                    "negation_handling",
                    "intensifier_scaling",
                    "emoji_sentiment_mapping",
                    "caps_booster",
                ],
            },
        )
