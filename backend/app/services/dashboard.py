"""
Phase 5.5 — Dashboard & Combined Analytics Orchestration Service.

Combines AnalyticsService queries with multi-layer analytical inference engines
(Sentiment, Topics, Trends, Network) into unified, frontend-friendly dashboard payloads.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.schemas.data_quality import AnalyticsReadyPost
from app.schemas.dashboard import (
    DashboardOverviewResponse,
    PlatformComparisonItem,
    PlatformComparisonResponse,
)
from app.services.analytics import AnalyticsService
from app.services.network import NetworkAnalysisService, get_network_analyzer
from app.services.sentiment import SentimentAnalysisService, get_sentiment_analyzer
from app.services.topic import TopicAnalysisService, get_topic_analyzer
from app.services.trend import TrendAnalysisService, get_trend_analyzer


class DashboardService:
    """Orchestrates multi-engine analytical pipelines over database datasets for dashboard consumption."""

    def __init__(
        self,
        db: Session,
        analytics_svc: Optional[AnalyticsService] = None,
        sentiment_svc: Optional[SentimentAnalysisService] = None,
        topic_svc: Optional[TopicAnalysisService] = None,
        trend_svc: Optional[TrendAnalysisService] = None,
        network_svc: Optional[NetworkAnalysisService] = None,
    ):
        self.db = db
        self.analytics_svc = analytics_svc or AnalyticsService(db)
        self.sentiment_svc = sentiment_svc or get_sentiment_analyzer()
        self.topic_svc = topic_svc or get_topic_analyzer()
        self.trend_svc = trend_svc or get_trend_analyzer()
        self.network_svc = network_svc or get_network_analyzer()

    def get_overview(
        self,
        platform: Optional[str] = None,
        language: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        search: Optional[str] = None,
        limit: int = 100,
    ) -> DashboardOverviewResponse:
        """Generates a high-level consolidated snapshot of social analytics matching filters."""
        # 1. Fetch matching post records once from database
        post_list = self.analytics_svc.get_posts(
            platform=platform,
            language=language,
            start_time=start_date,
            end_time=end_date,
            search=search,
            limit=limit,
            offset=0,
        )

        # 2. Get high-level database metrics
        eng_summary = self.analytics_svc.get_engagement_summary(
            platform=platform,
            language=language,
            start_time=start_date,
            end_time=end_date,
        )
        plat_summary = self.analytics_svc.get_platform_summary()
        if platform:
            plat_summary = [p for p in plat_summary if p.platform.lower() == platform.lower()]

        # 3. Convert fetched posts to AnalyticsReadyPost in memory to avoid N+1 queries
        ready_posts: List[AnalyticsReadyPost] = []
        for item in post_list.items:
            text_str = item.text or ""
            if text_str.strip():
                ready_posts.append(
                    AnalyticsReadyPost(
                        id=item.id,
                        platform=item.platform,
                        external_post_id=item.external_post_id,
                        text=text_str,
                        raw_text=text_str,
                        author_username=item.author_username,
                        author_display_name=item.author_display_name,
                        posted_at=item.posted_at,
                        collected_at=item.collected_at,
                        url=item.url,
                        language=item.language,
                        metrics=item.metrics,
                        metadata=item.metadata or {},
                        char_count=len(text_str),
                        word_count=len(text_str.split()),
                    )
                )

        # 4. Pass ready_posts to inference engines
        sentiment_res = self.sentiment_svc.analyze_batch(ready_posts) if ready_posts else None
        topic_res = self.topic_svc.extract_topics(ready_posts) if ready_posts else None
        trend_res = None
        if ready_posts and topic_res and topic_res.topics:
            trend_res = self.trend_svc.analyze_trends(
                topics=topic_res.topics,
                posts=ready_posts,
                window_duration=timedelta(hours=1),
            )
        network_res = self.network_svc.analyze_batch(ready_posts) if ready_posts else None

        return DashboardOverviewResponse(
            total_posts=post_list.total,
            engagement_summary=eng_summary,
            platforms=plat_summary,
            sentiment=sentiment_res,
            topics=topic_res,
            trends=trend_res,
            network=network_res,
            generated_at=datetime.now(timezone.utc),
        )

    def get_platform_comparison(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> PlatformComparisonResponse:
        """Computes comparative engagement and sentiment metrics grouped across platforms."""
        post_list = self.analytics_svc.get_posts(
            start_time=start_date,
            end_time=end_date,
            limit=500,
            offset=0,
        )

        ready_posts_by_platform: Dict[str, List[AnalyticsReadyPost]] = {}
        metrics_by_platform: Dict[str, Dict[str, Any]] = {}

        for item in post_list.items:
            plat = item.platform
            if plat not in metrics_by_platform:
                metrics_by_platform[plat] = {
                    "count": 0,
                    "likes": 0,
                    "comments": 0,
                    "shares": 0,
                    "views": 0,
                }
                ready_posts_by_platform[plat] = []

            metrics_by_platform[plat]["count"] += 1
            if item.metrics:
                metrics_by_platform[plat]["likes"] += item.metrics.likes
                metrics_by_platform[plat]["comments"] += item.metrics.comments
                metrics_by_platform[plat]["shares"] += item.metrics.shares
                metrics_by_platform[plat]["views"] += item.metrics.views

            text_str = item.text or ""
            if text_str.strip():
                ready_posts_by_platform[plat].append(
                    AnalyticsReadyPost(
                        id=item.id,
                        platform=item.platform,
                        external_post_id=item.external_post_id,
                        text=text_str,
                        raw_text=text_str,
                        author_username=item.author_username,
                        author_display_name=item.author_display_name,
                        posted_at=item.posted_at,
                        collected_at=item.collected_at,
                        url=item.url,
                        language=item.language,
                        metrics=item.metrics,
                        metadata=item.metadata or {},
                        char_count=len(text_str),
                        word_count=len(text_str.split()),
                    )
                )

        items: List[PlatformComparisonItem] = []
        for plat, m in metrics_by_platform.items():
            count = m["count"]
            tot_likes = m["likes"]
            tot_comments = m["comments"]
            tot_shares = m["shares"]
            tot_views = m["views"]
            avg_eng = round((tot_likes + tot_comments + tot_shares + tot_views) / count, 2) if count > 0 else 0.0

            sent_bd: Dict[str, int] = {"positive": 0, "neutral": 0, "negative": 0}
            r_posts = ready_posts_by_platform.get(plat, [])
            if r_posts:
                sent_res = self.sentiment_svc.analyze_batch(r_posts)
                sent_bd["positive"] = sent_res.positive_count
                sent_bd["neutral"] = sent_res.neutral_count
                sent_bd["negative"] = sent_res.negative_count

            items.append(
                PlatformComparisonItem(
                    platform=plat,
                    post_count=count,
                    total_likes=tot_likes,
                    total_comments=tot_comments,
                    total_shares=tot_shares,
                    total_views=tot_views,
                    avg_engagement=avg_eng,
                    sentiment_breakdown=sent_bd,
                )
            )

        return PlatformComparisonResponse(
            total_platforms=len(items),
            platforms=items,
            generated_at=datetime.now(timezone.utc),
        )
