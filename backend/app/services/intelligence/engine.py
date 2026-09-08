from datetime import datetime, timezone
import hashlib
import re
from typing import Any, Dict, List, Optional, Set

from app.schemas.dashboard import DashboardOverviewResponse, PlatformComparisonResponse
from app.schemas.data_quality import AnalyticsReadyPost
from app.schemas.intelligence import (
    BatchInsightResult,
    InsightEvidence,
    InsightItem,
    InsightSeverity,
    InsightStatus,
    InsightType,
)
from app.schemas.network import BatchNetworkResult
from app.schemas.sentiment import BatchSentimentResult
from app.schemas.topic import BatchTopicResult, ExtractedTopic
from app.schemas.trend import BatchTrendResult, TopicTrendResult
from app.services.intelligence.base import BaseIntelligenceEngine


def _slugify(text: str) -> str:
    """Converts a string into a clean lowercase alphanumeric slug."""
    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[-\s]+", "_", text)[:32] or "general"


def _generate_deterministic_id(insight_type: InsightType, scope_key: str, window_str: str = "") -> str:
    """Creates a deterministic, collision-resistant insight ID."""
    raw = f"{insight_type.value}:{scope_key}:{window_str}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:10]
    slug = _slugify(scope_key)
    return f"ins_{insight_type.value}_{slug}_{digest}"


class DeterministicIntelligenceEngine(BaseIntelligenceEngine):
    """
    Deterministic, explainable intelligence synthesis engine.
    Transforms raw statistical telemetry into evidence-grounded InsightItem objects.
    """

    def __init__(
        self,
        min_emerging_growth_pct: float = 30.0,
        min_emerging_volume: int = 2,
        spike_z_score_threshold: float = 2.0,
        min_spiking_volume: int = 4,
        min_sentiment_volume: int = 5,
        negative_ratio_threshold: float = 0.40,
        positive_ratio_threshold: float = 0.70,
        min_cross_platform_count: int = 2,
        min_cross_platform_posts: int = 3,
    ):
        self.min_emerging_growth_pct = min_emerging_growth_pct
        self.min_emerging_volume = min_emerging_volume
        self.spike_z_score_threshold = spike_z_score_threshold
        self.min_spiking_volume = min_spiking_volume
        self.min_sentiment_volume = min_sentiment_volume
        self.negative_ratio_threshold = negative_ratio_threshold
        self.positive_ratio_threshold = positive_ratio_threshold
        self.min_cross_platform_count = min_cross_platform_count
        self.min_cross_platform_posts = min_cross_platform_posts

    @property
    def model_name(self) -> str:
        return "insightx-intelligence-deterministic-v1"

    def generate_insights(
        self,
        trends: Optional[List[TopicTrendResult]] = None,
        batch_trend: Optional[BatchTrendResult] = None,
        topics: Optional[List[ExtractedTopic]] = None,
        batch_topic: Optional[BatchTopicResult] = None,
        sentiment: Optional[BatchSentimentResult] = None,
        overview: Optional[DashboardOverviewResponse] = None,
        platform_comparison: Optional[PlatformComparisonResponse] = None,
        network: Optional[BatchNetworkResult] = None,
        posts: Optional[List[AnalyticsReadyPost]] = None,
        min_confidence: float = 0.5,
        max_insights: int = 20,
    ) -> BatchInsightResult:
        """
        Synthesizes structured, evidence-grounded insights from multi-facet analytics.
        """
        resolved_trends: List[TopicTrendResult] = []
        if trends:
            resolved_trends.extend(trends)
        elif batch_trend and batch_trend.trends:
            resolved_trends.extend(batch_trend.trends)
        elif overview and overview.trends and overview.trends.trends:
            resolved_trends.extend(overview.trends.trends)

        resolved_sentiment: Optional[BatchSentimentResult] = (
            sentiment or (overview.sentiment if overview else None)
        )

        resolved_topics: List[ExtractedTopic] = []
        if topics:
            resolved_topics.extend(topics)
        elif batch_topic and batch_topic.topics:
            resolved_topics.extend(batch_topic.topics)
        elif overview and overview.topics and overview.topics.topics:
            resolved_topics.extend(overview.topics.topics)

        candidates: List[InsightItem] = []
        seen_ids: Set[str] = set()

        # 1. Evaluate Emerging Trends
        for trend in resolved_trends:
            insight = self._evaluate_emerging_trend(trend)
            if insight and insight.id not in seen_ids:
                seen_ids.add(insight.id)
                candidates.append(insight)

        # 2. Evaluate Anomalous Spikes
        for trend in resolved_trends:
            insight = self._evaluate_anomalous_spike(trend)
            if insight and insight.id not in seen_ids:
                seen_ids.add(insight.id)
                candidates.append(insight)

        # 3. Evaluate Polarized Sentiment Shifts
        if resolved_sentiment:
            insight = self._evaluate_sentiment_shift(resolved_sentiment, posts=posts)
            if insight and insight.id not in seen_ids:
                seen_ids.add(insight.id)
                candidates.append(insight)

        # 4. Evaluate Cross-Platform Narrative Propagation
        cross_insights = self._evaluate_cross_platform_propagation(
            resolved_topics=resolved_topics,
            posts=posts,
            overview=overview,
            platform_comparison=platform_comparison,
        )
        for insight in cross_insights:
            if insight.id not in seen_ids:
                seen_ids.add(insight.id)
                candidates.append(insight)

        # Filter by minimum confidence
        filtered = [c for c in candidates if c.confidence >= min_confidence]

        # Deterministic sorting: Severity weight descending, then confidence descending, then ID
        severity_order = {
            InsightSeverity.CRITICAL: 5,
            InsightSeverity.HIGH: 4,
            InsightSeverity.MEDIUM: 3,
            InsightSeverity.LOW: 2,
            InsightSeverity.INFO: 1,
        }
        filtered.sort(
            key=lambda item: (
                severity_order.get(item.severity, 0),
                item.confidence,
                item.id,
            ),
            reverse=True,
        )

        final_insights = filtered[:max_insights]

        # Aggregate counts
        crit = sum(1 for i in final_insights if i.severity == InsightSeverity.CRITICAL)
        high = sum(1 for i in final_insights if i.severity == InsightSeverity.HIGH)
        med = sum(1 for i in final_insights if i.severity == InsightSeverity.MEDIUM)
        low = sum(1 for i in final_insights if i.severity == InsightSeverity.LOW)
        info = sum(1 for i in final_insights if i.severity == InsightSeverity.INFO)

        return BatchInsightResult(
            total_insights=len(final_insights),
            critical_count=crit,
            high_count=high,
            medium_count=med,
            low_count=low,
            info_count=info,
            insights=final_insights,
            model=self.model_name,
            generated_at=datetime.now(timezone.utc),
        )

    def _evaluate_emerging_trend(self, trend: TopicTrendResult) -> Optional[InsightItem]:
        """Detects meaningful narrative growth relative to historical baseline."""
        if trend.current_volume < self.min_emerging_volume:
            return None

        is_qualifying_growth = (
            trend.is_emerging
            or (trend.growth_rate >= self.min_emerging_growth_pct and trend.growth_rate > 0)
        )
        if not is_qualifying_growth:
            return None

        # Build evidence
        z_val = trend.details.get("z_score") if trend.details else None
        evidence = InsightEvidence(
            topic_id=trend.topic_id,
            topic_label=trend.topic_label,
            growth_rate=trend.growth_rate,
            current_volume=trend.current_volume,
            baseline_volume=trend.baseline_volume,
            z_score=float(z_val) if z_val is not None else None,
            post_ids=list(trend.post_ids or []),
            external_post_ids=list(trend.external_post_ids or []),
            time_window=trend.current_window,
            raw_signals={
                "trend_score": trend.trend_score,
                "direction": trend.direction.value if hasattr(trend.direction, "value") else str(trend.direction),
                "is_emerging": trend.is_emerging,
            },
        )

        # Confidence calculation
        # Base 0.60 + volume boost (up to 0.20) + growth boost (up to 0.15) + post id boost (0.05)
        volume_boost = min(0.20, (trend.current_volume / 20.0) * 0.20)
        growth_boost = min(0.15, (max(0.0, trend.growth_rate) / 200.0) * 0.15)
        evidence_boost = 0.05 if (trend.post_ids and len(trend.post_ids) > 0) else 0.0
        confidence = round(min(0.98, max(0.50, 0.60 + volume_boost + growth_boost + evidence_boost)), 2)

        # Severity classification
        if trend.growth_rate >= 300.0 and trend.current_volume >= 20:
            severity = InsightSeverity.CRITICAL
        elif trend.growth_rate >= 100.0 and trend.current_volume >= 8:
            severity = InsightSeverity.HIGH
        elif trend.growth_rate >= 40.0 or trend.is_emerging:
            severity = InsightSeverity.MEDIUM
        else:
            severity = InsightSeverity.LOW

        window_str = f"{trend.current_window.start.isoformat()}_{trend.current_window.end.isoformat()}" if trend.current_window else ""
        insight_id = _generate_deterministic_id(InsightType.EMERGING_TREND, trend.topic_id or trend.topic_label, window_str)

        title = f"Emerging Narrative Signal: {trend.topic_label}"
        summary = (
            f"Topic '{trend.topic_label}' is demonstrating positive growth of {trend.growth_rate:.1f}% "
            f"({trend.current_volume} posts vs baseline of {trend.baseline_volume}) in the current observation window."
        )

        return InsightItem(
            id=insight_id,
            type=InsightType.EMERGING_TREND,
            title=title,
            summary=summary,
            severity=severity,
            confidence=confidence,
            affected_topic=trend.topic_label,
            evidence=evidence,
            recommended_action="Inspect supporting evidence posts in Posts Explorer to track narrative origin.",
            action_items=[
                "Review recent posts driving the topic's growth.",
                "Monitor velocity across successive observation windows for escalation.",
            ],
            status=InsightStatus.ACTIVE,
        )

    def _evaluate_anomalous_spike(self, trend: TopicTrendResult) -> Optional[InsightItem]:
        """Detects statistically significant volume surges above historical baseline."""
        if trend.current_volume < self.min_spiking_volume:
            return None

        z_val = trend.details.get("z_score") if trend.details else None
        z_score = float(z_val) if z_val is not None else 0.0

        is_qualifying_spike = trend.is_spiking or z_score >= self.spike_z_score_threshold
        if not is_qualifying_spike:
            return None

        evidence = InsightEvidence(
            topic_id=trend.topic_id,
            topic_label=trend.topic_label,
            growth_rate=trend.growth_rate,
            current_volume=trend.current_volume,
            baseline_volume=trend.baseline_volume,
            z_score=z_score,
            post_ids=list(trend.post_ids or []),
            external_post_ids=list(trend.external_post_ids or []),
            time_window=trend.current_window,
            raw_signals={
                "z_score": z_score,
                "is_spiking": trend.is_spiking,
                "trend_score": trend.trend_score,
            },
        )

        # Confidence calculation
        # Base 0.70 + z_score strength boost (up to 0.20) + volume boost (up to 0.08)
        z_boost = min(0.20, (max(0.0, z_score - 2.0) / 3.0) * 0.20)
        volume_boost = min(0.08, (trend.current_volume / 25.0) * 0.08)
        confidence = round(min(0.99, max(0.65, 0.70 + z_boost + volume_boost)), 2)

        # Severity classification
        if z_score >= 3.5 or (z_score >= 2.5 and trend.current_volume >= 25):
            severity = InsightSeverity.CRITICAL
        elif z_score >= 2.5 or trend.current_volume >= 10:
            severity = InsightSeverity.HIGH
        elif z_score >= 2.0:
            severity = InsightSeverity.MEDIUM
        else:
            severity = InsightSeverity.LOW

        window_str = f"{trend.current_window.start.isoformat()}_{trend.current_window.end.isoformat()}" if trend.current_window else ""
        insight_id = _generate_deterministic_id(InsightType.ANOMALOUS_SPIKE, trend.topic_id or trend.topic_label, window_str)

        title = f"Statistical Activity Spike: {trend.topic_label}"
        summary = (
            f"Unusual statistical volume spike detected for '{trend.topic_label}' "
            f"(z-score: {z_score:.2f}, {trend.current_volume} posts in current window vs baseline of {trend.baseline_volume})."
        )

        return InsightItem(
            id=insight_id,
            type=InsightType.ANOMALOUS_SPIKE,
            title=title,
            summary=summary,
            severity=severity,
            confidence=confidence,
            affected_topic=trend.topic_label,
            evidence=evidence,
            recommended_action="Verify if spike is driven by coordinated posting or a breaking event.",
            action_items=[
                "Analyze engagement distribution in Timeline & Trends.",
                "Cross-check top influencer handles in Network Graph.",
            ],
            status=InsightStatus.ACTIVE,
        )

    def _evaluate_sentiment_shift(
        self,
        sentiment: BatchSentimentResult,
        posts: Optional[List[AnalyticsReadyPost]] = None,
    ) -> Optional[InsightItem]:
        """Detects strong sentiment polarity concentrations or shifts across analyzed posts."""
        if sentiment.total_analyzed < self.min_sentiment_volume:
            return None

        neg_ratio = sentiment.negative_count / float(sentiment.total_analyzed)
        pos_ratio = sentiment.positive_count / float(sentiment.total_analyzed)

        is_negative_shift = neg_ratio >= self.negative_ratio_threshold or sentiment.average_score <= -0.25
        is_positive_shift = pos_ratio >= self.positive_ratio_threshold and sentiment.average_score >= 0.40

        if not (is_negative_shift or is_positive_shift):
            return None

        dominant_sentiment = "negative" if neg_ratio > pos_ratio else "positive"
        score_val = sentiment.average_score

        # Trace supporting post IDs and platforms
        post_ids = []
        external_post_ids = []
        platforms_set = set()

        if sentiment.results:
            for r in sentiment.results:
                if r.label == dominant_sentiment:
                    if r.post_id is not None:
                        post_ids.append(r.post_id)
                    if r.external_post_id:
                        external_post_ids.append(r.external_post_id)

        if posts:
            for p in posts:
                if p.platform:
                    platforms_set.add(p.platform)
                if not post_ids and p.id is not None:
                    post_ids.append(p.id)
                if not external_post_ids and p.external_post_id:
                    external_post_ids.append(p.external_post_id)

        evidence = InsightEvidence(
            sentiment_score=score_val,
            dominant_sentiment=dominant_sentiment,
            current_volume=sentiment.total_analyzed,
            post_ids=post_ids[:20],
            external_post_ids=external_post_ids[:20],
            platforms=sorted(list(platforms_set)),
            raw_signals={
                "positive_count": sentiment.positive_count,
                "negative_count": sentiment.negative_count,
                "neutral_count": sentiment.neutral_count,
                "average_score": score_val,
                "negative_ratio": round(neg_ratio, 3),
                "positive_ratio": round(pos_ratio, 3),
            },
        )

        # Confidence calculation
        # Base 0.65 + sample size boost (up to 0.25) + polarity magnitude boost (up to 0.08)
        sample_boost = min(0.25, (sentiment.total_analyzed / 50.0) * 0.25)
        polarity_boost = min(0.08, abs(score_val) * 0.08)
        confidence = round(min(0.98, max(0.55, 0.65 + sample_boost + polarity_boost)), 2)

        # Severity classification
        if dominant_sentiment == "negative":
            if neg_ratio >= 0.60 or score_val <= -0.50:
                severity = InsightSeverity.HIGH
            else:
                severity = InsightSeverity.MEDIUM
        else:
            severity = InsightSeverity.LOW

        insight_id = _generate_deterministic_id(
            InsightType.SENTIMENT_SHIFT,
            f"global_{dominant_sentiment}",
            f"{sentiment.total_analyzed}_{round(score_val, 2)}",
        )

        active_count = sentiment.negative_count if dominant_sentiment == "negative" else sentiment.positive_count
        title = f"Pronounced Sentiment Concentration: {dominant_sentiment.capitalize()} Tone"
        summary = (
            f"Dataset shows strong {dominant_sentiment} sentiment concentration "
            f"({active_count}/{sentiment.total_analyzed} posts, polarity score: {score_val:.2f})."
        )

        return InsightItem(
            id=insight_id,
            type=InsightType.SENTIMENT_SHIFT,
            title=title,
            summary=summary,
            severity=severity,
            confidence=confidence,
            affected_platforms=sorted(list(platforms_set)),
            evidence=evidence,
            recommended_action="Inspect driver keywords in Emotion & Sentiment radar to determine source of polarity.",
            action_items=[
                "Assess brand risk or public reception divergence.",
                "Review negative post excerpts in Posts Explorer.",
            ],
            status=InsightStatus.ACTIVE,
        )

    def _evaluate_cross_platform_propagation(
        self,
        resolved_topics: List[ExtractedTopic],
        posts: Optional[List[AnalyticsReadyPost]] = None,
        overview: Optional[DashboardOverviewResponse] = None,
        platform_comparison: Optional[PlatformComparisonResponse] = None,
    ) -> List[InsightItem]:
        """Detects narratives exhibiting active discussion across multiple distinct platforms."""
        insights: List[InsightItem] = []

        # If posts are provided, map topics to platform sets
        if posts and resolved_topics:
            post_id_map: Dict[int, AnalyticsReadyPost] = {p.id: p for p in posts if p.id is not None}
            ext_id_map: Dict[str, AnalyticsReadyPost] = {
                p.external_post_id: p for p in posts if p.external_post_id
            }

            for topic in resolved_topics:
                topic_posts: List[AnalyticsReadyPost] = []
                for pid in (topic.post_ids or []):
                    if pid in post_id_map:
                        topic_posts.append(post_id_map[pid])
                for ext in (topic.external_post_ids or []):
                    if ext in ext_id_map and ext_id_map[ext] not in topic_posts:
                        topic_posts.append(ext_id_map[ext])

                platforms = sorted(list(set(p.platform for p in topic_posts if p.platform)))
                if len(platforms) >= self.min_cross_platform_count and len(topic_posts) >= self.min_cross_platform_posts:
                    evidence = InsightEvidence(
                        topic_id=topic.topic_id,
                        topic_label=topic.label,
                        current_volume=len(topic_posts),
                        platforms=platforms,
                        post_ids=[p.id for p in topic_posts if p.id is not None],
                        external_post_ids=[p.external_post_id for p in topic_posts if p.external_post_id],
                        raw_signals={
                            "platform_count": len(platforms),
                            "platforms": platforms,
                        },
                    )

                    platform_boost = min(0.20, (len(platforms) - 1) * 0.08)
                    volume_boost = min(0.08, (len(topic_posts) / 20.0) * 0.08)
                    confidence = round(min(0.98, max(0.60, 0.70 + platform_boost + volume_boost)), 2)

                    severity = InsightSeverity.HIGH if (len(platforms) >= 3 and len(topic_posts) >= 15) else InsightSeverity.MEDIUM
                    insight_id = _generate_deterministic_id(
                        InsightType.CROSS_PLATFORM_PROPAGATION,
                        topic.topic_id or topic.label,
                        "_".join(platforms),
                    )

                    insights.append(
                        InsightItem(
                            id=insight_id,
                            type=InsightType.CROSS_PLATFORM_PROPAGATION,
                            title=f"Cross-Platform Propagation: {topic.label}",
                            summary=(
                                f"Narrative '{topic.label}' has active discussion distributed across "
                                f"{len(platforms)} distinct platforms ({', '.join(platforms)})."
                            ),
                            severity=severity,
                            confidence=confidence,
                            affected_topic=topic.label,
                            affected_platforms=platforms,
                            evidence=evidence,
                            recommended_action="Compare engagement velocity and sentiment divergence across platforms.",
                            action_items=[
                                "Trace initial seeding platform vs downstream amplification channels.",
                                "Examine cross-platform keyword variants in Posts Explorer.",
                            ],
                            status=InsightStatus.ACTIVE,
                        )
                    )

        # Alternatively, from platform comparison items if multiple active platforms exist
        if not insights and platform_comparison and platform_comparison.total_platforms >= self.min_cross_platform_count:
            active_plats = [p.platform for p in platform_comparison.platforms if p.post_count >= self.min_cross_platform_posts]
            if len(active_plats) >= self.min_cross_platform_count:
                total_posts = sum(p.post_count for p in platform_comparison.platforms if p.platform in active_plats)
                evidence = InsightEvidence(
                    platforms=active_plats,
                    current_volume=total_posts,
                    raw_signals={
                        "platform_distribution": {p.platform: p.post_count for p in platform_comparison.platforms},
                    },
                )
                confidence = 0.75
                severity = InsightSeverity.MEDIUM
                insight_id = _generate_deterministic_id(
                    InsightType.CROSS_PLATFORM_PROPAGATION,
                    "global_cross_platform",
                    "_".join(active_plats),
                )
                insights.append(
                    InsightItem(
                        id=insight_id,
                        type=InsightType.CROSS_PLATFORM_PROPAGATION,
                        title=f"Cross-Platform Multi-Stream Activity ({len(active_plats)} Platforms)",
                        summary=(
                            f"Multi-platform telemetry shows distributed social discourse spanning "
                            f"{len(active_plats)} channels ({', '.join(active_plats)}) with {total_posts} aggregate posts."
                        ),
                        severity=severity,
                        confidence=confidence,
                        affected_platforms=active_plats,
                        evidence=evidence,
                        recommended_action="Review comparative platform engagement metrics.",
                        action_items=[
                            "Check platform distribution in Multi-Platform Comparison chart.",
                        ],
                        status=InsightStatus.ACTIVE,
                    )
                )

        return insights
