from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.schemas.analytics_engine import (
    DetailedEngagementReport,
    DetailedNarrativeReport,
    DetailedSentimentReport,
    DetailedTrendReport,
    EngagementScoreBreakdown,
    IntervalUnit,
    NarrativeIntelligence,
    NarrativeLifecycleStage,
    Phase4AnalyticsReport,
    TemporalDynamicsReport,
)
from app.services.analytics_engine.base import BaseAnalyticsEngine
from app.services.analytics_engine.engagement import EngagementEngine
from app.services.analytics_engine.narrative import NarrativeDynamicsEngine
from app.services.analytics_engine.sentiment import SentimentAnalyticsEngine
from app.services.analytics_engine.time_series import (
    TimeSeriesDynamicsEngine,
    extract_post_timestamp,
)
from app.services.analytics_engine.trend import TrendAnalyticsEngine


class AnalyticsEngineService(BaseAnalyticsEngine):
    """
    Unified multi-dimensional Analytics Engine Service for InsightX (Phase 4).
    Synthesizes engagement analytics, temporal dynamics, sentiment analytics,
    trend momentum detection, narrative lifecycle modeling, and platform breakdown
    into actionable public intelligence.
    """

    def __init__(
        self,
        engagement_engine: Optional[EngagementEngine] = None,
        time_series_engine: Optional[TimeSeriesDynamicsEngine] = None,
        narrative_engine: Optional[NarrativeDynamicsEngine] = None,
        sentiment_engine: Optional[SentimentAnalyticsEngine] = None,
        trend_engine: Optional[TrendAnalyticsEngine] = None,
    ) -> None:
        self.engagement_engine = engagement_engine or EngagementEngine()
        self.sentiment_engine = sentiment_engine or SentimentAnalyticsEngine()
        self.time_series_engine = (
            time_series_engine
            or TimeSeriesDynamicsEngine(
                engagement_engine=self.engagement_engine,
                sentiment_engine=self.sentiment_engine,
            )
        )
        self.narrative_engine = (
            narrative_engine
            or NarrativeDynamicsEngine(
                engagement_engine=self.engagement_engine,
                sentiment_engine=self.sentiment_engine,
            )
        )
        self.trend_engine = trend_engine or TrendAnalyticsEngine(engagement_engine=self.engagement_engine)

    def _generate_summary_insights(
        self,
        engagement: EngagementScoreBreakdown,
        temporal: TemporalDynamicsReport,
        narratives: List[NarrativeIntelligence],
        platforms: Dict[str, EngagementScoreBreakdown],
        sentiment: Optional[DetailedSentimentReport] = None,
        trends: Optional[DetailedTrendReport] = None,
        detailed_narratives: Optional[DetailedNarrativeReport] = None,
    ) -> List[str]:
        """Generate structured text insights summarizing key analytical findings."""
        insights: List[str] = []

        if engagement.total_posts == 0:
            insights.append("No post data available for analytical evaluation.")
            return insights

        # Volume & Engagement insight
        insights.append(
            f"Evaluated {engagement.total_posts} posts with {engagement.total_likes:,} likes, "
            f"{engagement.total_comments:,} comments, and {engagement.total_shares:,} shares "
            f"(Weighted Engagement Score: {engagement.weighted_engagement_score:,.1f})."
        )

        # Virality / Discussion Depth insight
        if engagement.virality_index > 0.5:
            insights.append(
                f"High virality detected with a Virality Index of {engagement.virality_index:.2f} "
                f"({engagement.total_shares} shares relative to {engagement.total_likes} likes)."
            )
        elif engagement.discussion_depth > 0.5:
            insights.append(
                f"High community conversation depth observed (Discussion Depth: {engagement.discussion_depth:.2f})."
            )

        # Sentiment insight (Phase 4.3)
        if sentiment:
            dist = sentiment.overall_distribution
            insights.append(
                f"Overall sentiment is predominantly {dist.dominant_sentiment.upper()} "
                f"({dist.positive_percentage:.1f}% positive, {dist.neutral_percentage:.1f}% neutral, "
                f"{dist.negative_percentage:.1f}% negative, Net Sentiment Score: {dist.net_sentiment_score:+.2f})."
            )

        # Trend momentum insight (Phase 4.4)
        if trends and trends.ranked_trends:
            top_trend = trends.ranked_trends[0]
            insights.append(
                f"Leading momentum trend is '{top_trend.name}' ({top_trend.momentum.direction.upper()}, "
                f"Momentum Score: {top_trend.momentum.momentum_score:.1f}, "
                f"Growth: {top_trend.momentum.growth_rate_pct:+.1f}%)."
            )
            if trends.spiking_count > 0:
                insights.append(
                    f"Detected {trends.spiking_count} anomalous trending spike(s): "
                    + ", ".join(f"'{t.name}'" for t in trends.top_spiking_trends[:3])
                )

        # Narrative Intelligence insight (Phase 4.5)
        if detailed_narratives and detailed_narratives.ranked_narratives:
            dominant_n = detailed_narratives.dominant_narrative or detailed_narratives.ranked_narratives[0]
            stage_desc = dominant_n.lifecycle_stage.value.upper()
            insights.append(
                f"Leading narrative is '{dominant_n.label}' ({dominant_n.post_count} posts, "
                f"Impact Score: {dominant_n.narrative_impact_score:,.1f}, Stage: {stage_desc})."
            )

            if detailed_narratives.fastest_growing_narrative and detailed_narratives.fastest_growing_narrative.trajectory.volume_velocity > 0:
                fast_n = detailed_narratives.fastest_growing_narrative
                insights.append(
                    f"Fastest accelerating narrative: '{fast_n.label}' "
                    f"(Velocity: +{fast_n.trajectory.volume_velocity:.1f} posts/window)."
                )

            if detailed_narratives.cross_platform_narratives:
                cp_count = len(detailed_narratives.cross_platform_narratives)
                insights.append(
                    f"Identified {cp_count} multi-platform narrative(s) spanning multiple social ecosystems."
                )

            if detailed_narratives.emerging_count > 0:
                emerging_names = [n.label for n in detailed_narratives.ranked_narratives if n.lifecycle_stage == NarrativeLifecycleStage.EMERGING]
                insights.append(
                    f"Identified {detailed_narratives.emerging_count} emerging narrative cluster(s): "
                    + ", ".join(f"'{name}'" for name in emerging_names[:3])
                )
        elif narratives:
            top_narrative = narratives[0]
            stage_desc = top_narrative.lifecycle_stage.value.upper()
            insights.append(
                f"Primary narrative '{top_narrative.label}' ({top_narrative.post_count} posts) is currently {stage_desc}."
            )

        # Temporal peak insight
        if temporal.peak_bucket_start is not None and temporal.peak_bucket_volume > 0:
            peak_fmt = temporal.peak_bucket_start.strftime("%Y-%m-%d %H:%M UTC")
            insights.append(
                f"Peak activity occurred at {peak_fmt} with {temporal.peak_bucket_volume} posts "
                f"generating {temporal.peak_bucket_engagement:,.1f} weighted engagement."
            )

        # Temporal trajectory & anomaly insights (Phase 4.6)
        if temporal.trajectory_signal and temporal.trajectory_signal.classification != "insufficient_data":
            insights.append(
                f"Near-term signal trajectory is {temporal.trajectory_signal.classification.replace('_', ' ').upper()} ({temporal.trajectory_signal.explanation})."
            )

        if temporal.anomalous_intervals_count > 0:
            insights.append(
                f"Detected {temporal.anomalous_intervals_count} statistically significant activity spike(s) "
                f"exceeding the baseline threshold."
            )

        # Platform distribution insight
        if len(platforms) > 1:
            top_plat = max(platforms.items(), key=lambda x: x[1].weighted_engagement_score)
            insights.append(
                f"Dominant platform by engagement is '{top_plat[0]}' "
                f"({top_plat[1].total_posts} posts, {top_plat[1].weighted_engagement_score:,.1f} engagement score)."
            )

        return insights

    def analyze(
        self,
        posts: List[Any],
        topics: Optional[List[Any]] = None,
        interval_unit: IntervalUnit = IntervalUnit.HOUR,
        reference_time: Optional[datetime] = None,
        rolling_window_size: int = 3,
        anomaly_threshold_z: float = 2.0,
    ) -> Phase4AnalyticsReport:
        """
        Execute comprehensive Phase 4 analytical pipeline across provided social media posts.
        """
        analyzed_at = datetime.now(timezone.utc)

        if not posts:
            empty_eng = self.engagement_engine.calculate_engagement([])
            empty_temporal = self.time_series_engine.generate_time_series([], interval_unit=interval_unit)
            return Phase4AnalyticsReport(
                total_posts_evaluated=0,
                analyzed_at=analyzed_at,
                time_window_start=None,
                time_window_end=None,
                engagement_analytics=empty_eng,
                temporal_dynamics=empty_temporal,
                narratives=[],
                platform_breakdown={},
                detailed_engagement=None,
                detailed_sentiment=None,
                detailed_trends=None,
                detailed_narratives=None,
                summary_insights=["No posts provided for analysis."],
            )

        # 1. Engagement Analytics (Phase 4.1 & 4.2)
        engagement_breakdown = self.engagement_engine.calculate_engagement(posts)
        platform_breakdown = self.engagement_engine.calculate_platform_breakdown(posts)
        detailed_engagement = self.engagement_engine.generate_detailed_report(posts)

        # 2. Time-Series Dynamics (Phase 4.1)
        temporal_dynamics = self.time_series_engine.generate_time_series(
            posts=posts,
            interval_unit=interval_unit,
            rolling_window_size=rolling_window_size,
            anomaly_threshold_z=anomaly_threshold_z,
        )

        # 3. Sentiment Analytics (Phase 4.3)
        detailed_sentiment = self.sentiment_engine.generate_detailed_report(
            posts=posts,
            interval_unit=interval_unit,
        )

        # 4. Trend Analytics (Phase 4.4)
        detailed_trends = self.trend_engine.generate_detailed_report(
            posts=posts,
            topics=topics,
            reference_time=reference_time,
        )

        # 5. Narrative Dynamics & Intelligence (Phase 4.1 & 4.5)
        detailed_narratives = self.narrative_engine.generate_detailed_report(
            posts=posts,
            topics=topics,
            reference_time=reference_time,
        )
        narratives = detailed_narratives.ranked_narratives

        # Determine timestamps bounding window
        timestamps: List[datetime] = []
        for p in posts:
            ts = extract_post_timestamp(p)
            if ts:
                timestamps.append(ts)

        window_start = min(timestamps) if timestamps else None
        window_end = max(timestamps) if timestamps else None

        # 6. Summary Insights
        summary_insights = self._generate_summary_insights(
            engagement=engagement_breakdown,
            temporal=temporal_dynamics,
            narratives=narratives,
            platforms=platform_breakdown,
            sentiment=detailed_sentiment,
            trends=detailed_trends,
            detailed_narratives=detailed_narratives,
        )

        return Phase4AnalyticsReport(
            total_posts_evaluated=len(posts),
            analyzed_at=analyzed_at,
            time_window_start=window_start,
            time_window_end=window_end,
            engagement_analytics=engagement_breakdown,
            temporal_dynamics=temporal_dynamics,
            narratives=narratives,
            platform_breakdown=platform_breakdown,
            detailed_engagement=detailed_engagement,
            detailed_sentiment=detailed_sentiment,
            detailed_trends=detailed_trends,
            detailed_narratives=detailed_narratives,
            summary_insights=summary_insights,
        )


_analytics_engine_service_instance: Optional[AnalyticsEngineService] = None


def get_analytics_engine_service() -> AnalyticsEngineService:
    """FastAPI dependency provider returning singleton AnalyticsEngineService instance."""
    global _analytics_engine_service_instance
    if _analytics_engine_service_instance is None:
        _analytics_engine_service_instance = AnalyticsEngineService()
    return _analytics_engine_service_instance
