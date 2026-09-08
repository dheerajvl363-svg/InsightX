from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.schemas.analytics_engine import (
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
from app.services.analytics_engine.time_series import (
    TimeSeriesDynamicsEngine,
    extract_post_timestamp,
)


class AnalyticsEngineService(BaseAnalyticsEngine):
    """
    Unified multi-dimensional Analytics Engine Service for InsightX (Phase 4.1).
    Synthesizes engagement analytics, temporal dynamics, narrative lifecycle modeling,
    and platform breakdown into actionable public intelligence.
    """

    def __init__(
        self,
        engagement_engine: Optional[EngagementEngine] = None,
        time_series_engine: Optional[TimeSeriesDynamicsEngine] = None,
        narrative_engine: Optional[NarrativeDynamicsEngine] = None,
    ) -> None:
        self.engagement_engine = engagement_engine or EngagementEngine()
        self.time_series_engine = (
            time_series_engine or TimeSeriesDynamicsEngine(engagement_engine=self.engagement_engine)
        )
        self.narrative_engine = (
            narrative_engine or NarrativeDynamicsEngine(engagement_engine=self.engagement_engine)
        )

    def _generate_summary_insights(
        self,
        engagement: EngagementScoreBreakdown,
        temporal: TemporalDynamicsReport,
        narratives: List[NarrativeIntelligence],
        platforms: Dict[str, EngagementScoreBreakdown],
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

        # Temporal peak insight
        if temporal.peak_bucket_start is not None and temporal.peak_bucket_volume > 0:
            peak_fmt = temporal.peak_bucket_start.strftime("%Y-%m-%d %H:%M UTC")
            insights.append(
                f"Peak activity occurred at {peak_fmt} with {temporal.peak_bucket_volume} posts "
                f"generating {temporal.peak_bucket_engagement:,.1f} weighted engagement."
            )

        # Anomaly insight
        if temporal.anomalous_intervals_count > 0:
            insights.append(
                f"Detected {temporal.anomalous_intervals_count} statistically significant activity spike(s) "
                f"exceeding the baseline threshold."
            )

        # Narrative lifecycle insight
        if narratives:
            top_narrative = narratives[0]
            stage_desc = top_narrative.lifecycle_stage.value.upper()
            insights.append(
                f"Primary narrative '{top_narrative.label}' ({top_narrative.post_count} posts) is currently {stage_desc}."
            )

            emerging = [n for n in narratives if n.lifecycle_stage == NarrativeLifecycleStage.EMERGING]
            if emerging:
                insights.append(
                    f"Identified {len(emerging)} emerging narrative cluster(s): "
                    + ", ".join(f"'{n.label}'" for n in emerging[:3])
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
                summary_insights=["No posts provided for analysis."],
            )

        # 1. Engagement Analytics
        engagement_breakdown = self.engagement_engine.calculate_engagement(posts)
        platform_breakdown = self.engagement_engine.calculate_platform_breakdown(posts)
        detailed_engagement = self.engagement_engine.generate_detailed_report(posts)

        # 2. Time-Series Dynamics
        temporal_dynamics = self.time_series_engine.generate_time_series(
            posts=posts,
            interval_unit=interval_unit,
            rolling_window_size=rolling_window_size,
            anomaly_threshold_z=anomaly_threshold_z,
        )

        # 3. Narrative Dynamics & Lifecycles
        narratives = self.narrative_engine.analyze_narratives(
            posts=posts,
            topics=topics,
            reference_time=reference_time,
        )

        # Determine timestamps bounding window
        timestamps: List[datetime] = []
        for p in posts:
            ts = extract_post_timestamp(p)
            if ts:
                timestamps.append(ts)

        window_start = min(timestamps) if timestamps else None
        window_end = max(timestamps) if timestamps else None

        # 4. Summary Insights
        summary_insights = self._generate_summary_insights(
            engagement=engagement_breakdown,
            temporal=temporal_dynamics,
            narratives=narratives,
            platforms=platform_breakdown,
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
            summary_insights=summary_insights,
        )
