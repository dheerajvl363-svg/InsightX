import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.api.routes.analytics import (
    _fetch_db_posts_as_analytics_ready,
    _resolve_analytics_posts,
    get_dashboard_service,
    get_network_service,
    get_sentiment_service,
    get_topic_service,
    get_trend_service,
)
from app.database import get_db
from app.schemas.data_quality import AnalyticsReadyPost
from app.schemas.intelligence import (
    BatchExplanationResult,
    BatchInsightResult,
    InsightExplanation,
    InsightItem,
    UnifiedWorkflowResult,
)
from app.schemas.post import RawPostPayload
from app.schemas.topic import ExtractedTopic
from app.schemas.trend import TopicTrendResult
from app.services.dashboard import DashboardService
from app.services.intelligence.explanation import (
    DeterministicExplanationEngine,
    get_explanation_engine,
)
from app.services.intelligence.service import (
    IntelligenceAnalysisService,
    get_intelligence_analyzer,
)
from app.services.network import NetworkAnalysisService
from app.services.sentiment import SentimentAnalysisService
from app.services.topic import TopicAnalysisService
from app.services.trend import TrendAnalysisService

logger = logging.getLogger(__name__)


class UnifiedIntelligenceWorkflow:
    """
    End-to-End Unified Intelligence Pipeline Orchestrator.
    Connects:
      Raw/normalized posts
      → Multi-facet analytics (Sentiment, Topics, Trends, Network, Overview)
      → Deterministic anomaly & narrative detection
      → Auditable explanation generation
      → Traceable evidence provenance references
    """

    def __init__(
        self,
        sentiment_service: Optional[SentimentAnalysisService] = None,
        topic_service: Optional[TopicAnalysisService] = None,
        trend_service: Optional[TrendAnalysisService] = None,
        network_service: Optional[NetworkAnalysisService] = None,
        dashboard_service: Optional[DashboardService] = None,
        intelligence_service: Optional[IntelligenceAnalysisService] = None,
        explanation_engine: Optional[DeterministicExplanationEngine] = None,
    ):
        self.sentiment_service = sentiment_service or SentimentAnalysisService()
        self.topic_service = topic_service or TopicAnalysisService()
        self.trend_service = trend_service or TrendAnalysisService()
        self.network_service = network_service or NetworkAnalysisService()
        self.dashboard_service = dashboard_service
        self.intelligence_service = intelligence_service or get_intelligence_analyzer()
        self.explanation_engine = explanation_engine or get_explanation_engine()

    @property
    def model_name(self) -> str:
        return f"insightx-unified-workflow-v1 ({self.intelligence_service.model_name})"

    def resolve_posts(
        self,
        posts: Optional[List[AnalyticsReadyPost]] = None,
        raw_posts: Optional[List[RawPostPayload]] = None,
        db: Optional[Session] = None,
        platform: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 200,
    ) -> List[AnalyticsReadyPost]:
        """
        Resolves posts from in-memory objects or database query into normalized AnalyticsReadyPost instances.
        """
        if posts or raw_posts:
            return _resolve_analytics_posts(posts=posts, raw_posts=raw_posts)

        if db is not None:
            end_time = end_date or datetime.now(timezone.utc)
            start_time = start_date or (end_time - timedelta(days=1))
            return _fetch_db_posts_as_analytics_ready(
                db=db,
                platform=platform,
                start_date=start_time,
                end_date=end_time,
                limit=limit,
            )

        return []

    def run_workflow(
        self,
        posts: Optional[List[AnalyticsReadyPost]] = None,
        raw_posts: Optional[List[RawPostPayload]] = None,
        topics: Optional[List[ExtractedTopic]] = None,
        trends: Optional[List[TopicTrendResult]] = None,
        db: Optional[Session] = None,
        platform: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        min_confidence: float = 0.5,
        max_insights: int = 20,
        generate_explanations: bool = True,
    ) -> UnifiedWorkflowResult:
        """
        Executes the unified end-to-end intelligence workflow.
        """
        resolved_posts = self.resolve_posts(
            posts=posts,
            raw_posts=raw_posts,
            db=db,
            platform=platform,
            start_date=start_date,
            end_date=end_date,
        )

        now = datetime.now(timezone.utc)

        # Handle empty dataset cleanly without errors
        if not resolved_posts and not topics and not trends:
            empty_insights = BatchInsightResult(
                total_insights=0,
                insights=[],
                model=self.intelligence_service.model_name,
                generated_at=now,
            )
            return UnifiedWorkflowResult(
                total_insights=0,
                total_explanations=0,
                batch_insights=empty_insights,
                explanations=[],
                analytics_summary={"total_posts": 0, "status": "empty_dataset"},
                model=self.model_name,
                generated_at=now,
            )

        # Stage 1: Execute intermediate multi-facet analytics
        sentiment_res = None
        topic_res = None
        trend_res = None
        network_res = None
        overview_res = (
            self.dashboard_service.get_overview(platform=platform)
            if self.dashboard_service and platform
            else None
        )

        if resolved_posts:
            sentiment_res = self.sentiment_service.analyze_batch(resolved_posts)

            if not topics:
                topic_res = self.topic_service.extract_topics(resolved_posts)
                resolved_topics = topic_res.topics
            else:
                resolved_topics = topics

            if not trends and resolved_topics:
                trend_res = self.trend_service.analyze_trends(topics=resolved_topics, posts=resolved_posts)
                resolved_trends = trend_res.trends
            else:
                resolved_trends = trends or []

            network_res = self.network_service.analyze_batch(resolved_posts)
        else:
            resolved_topics = topics or []
            resolved_trends = trends or []

        # Stage 2: Synthesize evidence-grounded intelligence insights
        batch_insights = self.intelligence_service.generate_insights(
            trends=resolved_trends,
            batch_trend=trend_res,
            topics=resolved_topics,
            batch_topic=topic_res,
            sentiment=sentiment_res,
            overview=overview_res,
            network=network_res,
            posts=resolved_posts if resolved_posts else None,
            min_confidence=min_confidence,
            max_insights=max_insights,
        )

        # Stage 3: Generate auditable explanations for all candidate insights
        explanations: List[InsightExplanation] = []
        if generate_explanations and batch_insights.insights:
            batch_expl = self.explanation_engine.explain_batch(batch_insight=batch_insights)
            explanations = batch_expl.explanations

        # Stage 4: Package unified report
        platforms_detected = list({p.platform for p in resolved_posts if p.platform})
        analytics_summary: Dict[str, Any] = {
            "total_posts": len(resolved_posts),
            "platforms_detected": platforms_detected,
            "average_sentiment": round(sentiment_res.average_score, 3) if sentiment_res else 0.0,
            "total_topics_found": len(resolved_topics),
            "total_trends_evaluated": len(resolved_trends),
        }

        return UnifiedWorkflowResult(
            total_insights=batch_insights.total_insights,
            total_explanations=len(explanations),
            batch_insights=batch_insights,
            explanations=explanations,
            analytics_summary=analytics_summary,
            model=self.model_name,
            generated_at=now,
        )

    def get_insight_explanation(
        self,
        insight_id: str,
        platform: Optional[str] = None,
        db: Optional[Session] = None,
        posts: Optional[List[AnalyticsReadyPost]] = None,
        raw_posts: Optional[List[RawPostPayload]] = None,
    ) -> InsightExplanation:
        """
        Resolves and explains an individual insight deterministically using the unified pipeline.
        """
        workflow_res = self.run_workflow(
            posts=posts,
            raw_posts=raw_posts,
            db=db,
            platform=platform,
            generate_explanations=True,
        )

        for expl in workflow_res.explanations:
            if expl.insight_id == insight_id:
                return expl

        # If not already generated in batch, check individual insight candidate
        for item in workflow_res.batch_insights.insights:
            if item.id == insight_id:
                return self.explanation_engine.explain_insight(item)

        raise LookupError(f"Insight '{insight_id}' not found in recent synthesized intelligence.")


def get_unified_workflow(
    db: Session = None,
) -> UnifiedIntelligenceWorkflow:
    """
    Factory creating a UnifiedIntelligenceWorkflow instance with fully wired dependencies.
    """
    dashboard_srv = DashboardService(db=db) if db is not None else None
    return UnifiedIntelligenceWorkflow(
        sentiment_service=SentimentAnalysisService(),
        topic_service=TopicAnalysisService(),
        trend_service=TrendAnalysisService(),
        network_service=NetworkAnalysisService(),
        dashboard_service=dashboard_srv,
        intelligence_service=get_intelligence_analyzer(),
        explanation_engine=get_explanation_engine(),
    )
