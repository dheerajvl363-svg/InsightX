from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.metric import PostMetric
from app.models.platform import Platform
from app.models.post import Post
from app.models.user import User
from app.schemas.analytics import (
    AuthorListResponse,
    AuthorSummary,
    CountResponse,
    EngagementSummary,
    LanguageSummary,
    PlatformSummary,
    PostListResponse,
    PostSummary,
    TimeSeriesPoint,
    TimeSeriesResponse,
)
from app.schemas.post import PostMetricsSchema

logger = logging.getLogger(__name__)


def _normalize_datetime_for_db(value: Optional[datetime]) -> Optional[datetime]:
    """
    Normalizes datetime values before comparing with timezone-naive database columns:
    - If timezone-aware: converts to UTC and removes tzinfo.
    - If timezone-naive: leaves unchanged.
    """
    if value is None:
        return None
    if value.tzinfo is not None and value.tzinfo.utcoffset(value) is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


ALLOWED_SORT_BY = {"posted_at", "likes", "comments", "shares", "views"}
ALLOWED_AUTHOR_SORT_BY = {
    "post_count",
    "total_likes",
    "total_comments",
    "total_shares",
    "total_views",
}
ALLOWED_ORDER = {"asc", "desc"}


class AnalyticsService:
    """
    Dedicated read-only query service for social-media analytics and ML/NLP pipelines.
    Enforces deterministic querying, pagination, and multi-dimensional aggregations.
    """

    _normalize_datetime_for_db = staticmethod(_normalize_datetime_for_db)

    def __init__(self, db: Session):
        self.db = db

    def _latest_metric_subquery(self):
        """
        Builds a subquery that, for each post, surfaces the latest metric snapshot's
        likes/comments/shares/views based on collected_at (with id as tie-breaker),
        defaulting nulls to 0 via COALESCE.
        Used for engagement filtering and sorting.
        """
        ranked_metrics = (
            self.db.query(
                PostMetric.post_id.label("post_id"),
                func.coalesce(PostMetric.likes, 0).label("likes"),
                func.coalesce(PostMetric.comments, 0).label("comments"),
                func.coalesce(PostMetric.shares, 0).label("shares"),
                func.coalesce(PostMetric.views, 0).label("views"),
                func.row_number()
                .over(
                    partition_by=PostMetric.post_id,
                    order_by=(PostMetric.collected_at.desc(), PostMetric.id.desc()),
                )
                .label("rn"),
            )
            .subquery()
        )
        return (
            self.db.query(
                ranked_metrics.c.post_id,
                ranked_metrics.c.likes,
                ranked_metrics.c.comments,
                ranked_metrics.c.shares,
                ranked_metrics.c.views,
            )
            .filter(ranked_metrics.c.rn == 1)
            .subquery()
        )

    def _apply_filters(
        self,
        query,
        platform: Optional[str] = None,
        language: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        author_username: Optional[str] = None,
        search: Optional[str] = None,
        min_likes: Optional[int] = None,
        min_comments: Optional[int] = None,
        min_shares: Optional[int] = None,
        min_views: Optional[int] = None,
        metric_subquery: Optional[Any] = None,
    ):
        """Applies standardized query filters across post queries."""
        if platform and platform.strip():
            query = query.join(Post.platform).filter(
                func.lower(Platform.name) == platform.strip().lower()
            )

        if language and language.strip():
            query = query.filter(func.lower(Post.language) == language.strip().lower())

        norm_start_time = self._normalize_datetime_for_db(start_time)
        if norm_start_time is not None:
            query = query.filter(Post.posted_at >= norm_start_time)

        norm_end_time = self._normalize_datetime_for_db(end_time)
        if norm_end_time is not None:
            query = query.filter(Post.posted_at <= norm_end_time)

        if author_username and author_username.strip():
            clean_user = author_username.strip().lstrip("@").lower()
            query = query.join(Post.user).filter(func.lower(User.username) == clean_user)

        if search and search.strip():
            query = query.filter(Post.text.ilike(f"%{search.strip()}%"))

        # Engagement filters & sorting join — join latest-metric subquery only when needed
        engagement_requested = any(
            v is not None for v in (min_likes, min_comments, min_shares, min_views)
        )
        if engagement_requested or metric_subquery is not None:
            if metric_subquery is None:
                metric_subquery = self._latest_metric_subquery()
            query = query.outerjoin(metric_subquery, Post.id == metric_subquery.c.post_id)
            if min_likes is not None:
                query = query.filter(
                    func.coalesce(metric_subquery.c.likes, 0) >= min_likes
                )
            if min_comments is not None:
                query = query.filter(
                    func.coalesce(metric_subquery.c.comments, 0) >= min_comments
                )
            if min_shares is not None:
                query = query.filter(
                    func.coalesce(metric_subquery.c.shares, 0) >= min_shares
                )
            if min_views is not None:
                query = query.filter(
                    func.coalesce(metric_subquery.c.views, 0) >= min_views
                )

        return query

    def get_posts(
        self,
        platform: Optional[str] = None,
        language: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        author_username: Optional[str] = None,
        search: Optional[str] = None,
        min_likes: Optional[int] = None,
        min_comments: Optional[int] = None,
        min_shares: Optional[int] = None,
        min_views: Optional[int] = None,
        sort_by: str = "posted_at",
        order: str = "desc",
        limit: int = 50,
        offset: int = 0,
    ) -> PostListResponse:
        """
        Retrieves a paginated, deterministically ordered list of posts with latest metrics.
        Supports sorting by posted_at or latest snapshot engagement metrics.
        """
        # Validate sort parameters
        clean_sort_by = (sort_by or "posted_at").strip().lower()
        if clean_sort_by not in ALLOWED_SORT_BY:
            raise ValueError(
                f"Invalid sort_by field '{sort_by}'. Supported fields: {', '.join(sorted(ALLOWED_SORT_BY))}."
            )

        clean_order = (order or "desc").strip().lower()
        if clean_order not in ALLOWED_ORDER:
            raise ValueError(
                f"Invalid order '{order}'. Supported orders: {', '.join(sorted(ALLOWED_ORDER))}."
            )

        is_desc = (clean_order == "desc")
        needs_metric_subq = (
            clean_sort_by in ("likes", "comments", "shares", "views")
            or any(v is not None for v in (min_likes, min_comments, min_shares, min_views))
        )
        metric_sq = self._latest_metric_subquery() if needs_metric_subq else None

        # Base query for counting
        base_query = self.db.query(Post)
        filtered_query = self._apply_filters(
            base_query,
            platform=platform,
            language=language,
            start_time=start_time,
            end_time=end_time,
            author_username=author_username,
            search=search,
            min_likes=min_likes,
            min_comments=min_comments,
            min_shares=min_shares,
            min_views=min_views,
            metric_subquery=metric_sq,
        )

        total = filtered_query.count()

        # Build deterministic ordering
        if clean_sort_by == "posted_at":
            primary_col = Post.posted_at.desc() if is_desc else Post.posted_at.asc()
            tie_breaker = Post.id.desc() if is_desc else Post.id.asc()
            order_by_clauses = [primary_col, tie_breaker]
        else:
            metric_col = getattr(metric_sq.c, clean_sort_by)
            primary_col = (
                func.coalesce(metric_col, 0).desc()
                if is_desc
                else func.coalesce(metric_col, 0).asc()
            )
            secondary_col = Post.posted_at.desc() if is_desc else Post.posted_at.asc()
            tie_breaker = Post.id.desc() if is_desc else Post.id.asc()
            order_by_clauses = [primary_col, secondary_col, tie_breaker]

        # Deterministic ordering and pagination
        posts = (
            filtered_query.order_by(*order_by_clauses)
            .offset(offset)
            .limit(limit)
            .all()
        )

        items: List[PostSummary] = []
        for post in posts:
            # Retrieve latest metric snapshot if present
            latest_metric = None
            if post.metrics:
                # Sort by collected_at descending, tie-breaking by id descending
                sorted_metrics = sorted(
                    post.metrics,
                    key=lambda m: (
                        m.collected_at if m.collected_at is not None else datetime.min,
                        m.id if m.id is not None else 0,
                    ),
                    reverse=True,
                )
                latest_metric = sorted_metrics[0]

            metric_schema = None
            if latest_metric:
                metric_schema = PostMetricsSchema(
                    likes=latest_metric.likes or 0,
                    comments=latest_metric.comments or 0,
                    shares=latest_metric.shares or 0,
                    views=latest_metric.views or 0,
                    collected_at=latest_metric.collected_at,
                )

            items.append(
                PostSummary(
                    id=post.id,
                    platform=post.platform.name if post.platform else "Unknown",
                    external_post_id=post.external_post_id,
                    text=post.text,
                    author_username=post.user.username if post.user else None,
                    author_display_name=post.user.display_name if post.user else None,
                    posted_at=post.posted_at,
                    collected_at=post.collected_at,
                    url=post.url,
                    language=post.language,
                    metrics=metric_schema,
                    metadata=post.post_metadata,
                )
            )

        return PostListResponse(total=total, limit=limit, offset=offset, items=items)

    def get_post_count(
        self,
        platform: Optional[str] = None,
        language: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        author_username: Optional[str] = None,
        search: Optional[str] = None,
        min_likes: Optional[int] = None,
        min_comments: Optional[int] = None,
        min_shares: Optional[int] = None,
        min_views: Optional[int] = None,
    ) -> CountResponse:
        """Returns count of posts matching filters."""
        query = self.db.query(Post)
        filtered_query = self._apply_filters(
            query,
            platform=platform,
            language=language,
            start_time=start_time,
            end_time=end_time,
            author_username=author_username,
            search=search,
            min_likes=min_likes,
            min_comments=min_comments,
            min_shares=min_shares,
            min_views=min_views,
        )

        count = filtered_query.count()
        applied = {
            k: str(v)
            for k, v in {
                "platform": platform,
                "language": language,
                "start_time": start_time,
                "end_time": end_time,
                "author_username": author_username,
                "search": search,
                "min_likes": min_likes,
                "min_comments": min_comments,
                "min_shares": min_shares,
                "min_views": min_views,
            }.items()
            if v is not None
        }

        return CountResponse(count=count, filters_applied=applied)

    def get_engagement_summary(
        self,
        platform: Optional[str] = None,
        language: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> EngagementSummary:
        """
        Computes aggregate engagement metrics (likes, comments, shares, views)
        using the latest snapshot for each post.
        """
        # Subquery to identify the latest metric snapshot ID per post
        latest_metric_subq = (
            self.db.query(
                PostMetric.post_id,
                func.max(PostMetric.id).label("latest_metric_id"),
            )
            .group_by(PostMetric.post_id)
            .subquery()
        )

        query = (
            self.db.query(
                func.count(Post.id).label("total_posts"),
                func.count(PostMetric.id).label("posts_with_metrics"),
                func.coalesce(func.sum(PostMetric.likes), 0).label("total_likes"),
                func.coalesce(func.sum(PostMetric.comments), 0).label("total_comments"),
                func.coalesce(func.sum(PostMetric.shares), 0).label("total_shares"),
                func.coalesce(func.sum(PostMetric.views), 0).label("total_views"),
            )
            .outerjoin(latest_metric_subq, Post.id == latest_metric_subq.c.post_id)
            .outerjoin(PostMetric, PostMetric.id == latest_metric_subq.c.latest_metric_id)
        )

        filtered_query = self._apply_filters(
            query,
            platform=platform,
            language=language,
            start_time=start_time,
            end_time=end_time,
        )

        row = filtered_query.first()
        total_posts = row.total_posts if row else 0
        posts_with_metrics = row.posts_with_metrics if row else 0
        total_likes = int(row.total_likes) if row else 0
        total_comments = int(row.total_comments) if row else 0
        total_shares = int(row.total_shares) if row else 0
        total_views = int(row.total_views) if row else 0

        # Calculate averages based on analyzed posts
        divisor = float(total_posts) if total_posts > 0 else 1.0
        avg_likes = round(total_likes / divisor, 2)
        avg_comments = round(total_comments / divisor, 2)
        avg_shares = round(total_shares / divisor, 2)
        avg_views = round(total_views / divisor, 2)

        return EngagementSummary(
            total_posts_analyzed=total_posts,
            posts_with_metrics=posts_with_metrics,
            total_likes=total_likes,
            total_comments=total_comments,
            total_shares=total_shares,
            total_views=total_views,
            avg_likes=avg_likes,
            avg_comments=avg_comments,
            avg_shares=avg_shares,
            avg_views=avg_views,
        )

    def get_platform_summary(self) -> List[PlatformSummary]:
        """
        Returns post count and chronological bounds grouped by platform.
        """
        results = (
            self.db.query(
                Platform.name,
                func.count(Post.id).label("post_count"),
                func.min(Post.posted_at).label("earliest_post"),
                func.max(Post.posted_at).label("latest_post"),
            )
            .outerjoin(Post, Post.platform_id == Platform.id)
            .group_by(Platform.name)
            .order_by(func.count(Post.id).desc())
            .all()
        )

        return [
            PlatformSummary(
                platform=row.name,
                post_count=row.post_count,
                earliest_post=row.earliest_post,
                latest_post=row.latest_post,
            )
            for row in results
        ]

    def get_language_summary(self) -> List[LanguageSummary]:
        """
        Returns post count grouped by language.
        """
        results = (
            self.db.query(
                func.coalesce(Post.language, "unspecified").label("lang"),
                func.count(Post.id).label("post_count"),
            )
            .group_by(func.coalesce(Post.language, "unspecified"))
            .order_by(func.count(Post.id).desc())
            .all()
        )

        return [
            LanguageSummary(
                language=row.lang,
                post_count=row.post_count,
            )
            for row in results
        ]

    def get_time_series(
        self,
        platform: Optional[str] = None,
        language: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> TimeSeriesResponse:
        """
        Aggregates daily post counts chronologically.
        """
        day_expr = func.date(Post.posted_at)

        query = self.db.query(
            day_expr.label("day"),
            func.count(Post.id).label("count"),
        )

        filtered_query = self._apply_filters(
            query,
            platform=platform,
            language=language,
            start_time=start_time,
            end_time=end_time,
        )

        rows = (
            filtered_query.group_by(day_expr)
            .order_by(day_expr.asc())
            .all()
        )

        points = [
            TimeSeriesPoint(
                date=str(row.day),
                count=row.count,
            )
            for row in rows
        ]

        return TimeSeriesResponse(
            interval="day",
            total_points=len(points),
            points=points,
        )

    def get_author_summary(
        self,
        platform: Optional[str] = None,
        language: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        search: Optional[str] = None,
        sort_by: str = "post_count",
        order: str = "desc",
        limit: int = 50,
        offset: int = 0,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> AuthorListResponse:
        """
        Aggregates author-level analytics (post count, latest metric engagement totals & averages)
        grouped by author and platform.
        Supports filtering on posts before aggregation, and sorting on SQL aggregate fields.
        """
        # Validate sort parameters
        clean_sort_by = (sort_by or "post_count").strip().lower()
        if clean_sort_by not in ALLOWED_AUTHOR_SORT_BY:
            raise ValueError(
                f"Invalid sort_by field '{sort_by}'. Supported fields: {', '.join(sorted(ALLOWED_AUTHOR_SORT_BY))}."
            )

        clean_order = (order or "desc").strip().lower()
        if clean_order not in ALLOWED_ORDER:
            raise ValueError(
                f"Invalid order '{order}'. Supported orders: {', '.join(sorted(ALLOWED_ORDER))}."
            )

        effective_start = start_date if start_date is not None else start_time
        effective_end = end_date if end_date is not None else end_time

        # 1. Filter posts before author aggregation
        filtered_posts = self._apply_filters(
            self.db.query(Post),
            platform=platform,
            language=language,
            start_time=effective_start,
            end_time=effective_end,
            search=search,
        ).subquery()

        # 2. Latest metric snapshot per post
        metric_sq = self._latest_metric_subquery()

        # 3. Aggregates
        post_count_col = func.count(filtered_posts.c.id).label("post_count")
        total_likes_col = func.coalesce(func.sum(metric_sq.c.likes), 0).label("total_likes")
        total_comments_col = func.coalesce(func.sum(metric_sq.c.comments), 0).label("total_comments")
        total_shares_col = func.coalesce(func.sum(metric_sq.c.shares), 0).label("total_shares")
        total_views_col = func.coalesce(func.sum(metric_sq.c.views), 0).label("total_views")
        earliest_post_col = func.min(filtered_posts.c.posted_at).label("earliest_post")
        latest_post_col = func.max(filtered_posts.c.posted_at).label("latest_post")

        query = (
            self.db.query(
                User.username.label("username"),
                User.display_name.label("display_name"),
                Platform.name.label("platform"),
                post_count_col,
                total_likes_col,
                total_comments_col,
                total_shares_col,
                total_views_col,
                earliest_post_col,
                latest_post_col,
            )
            .join(User, filtered_posts.c.user_id == User.id)
            .join(Platform, User.platform_id == Platform.id)
            .outerjoin(metric_sq, filtered_posts.c.id == metric_sq.c.post_id)
            .group_by(User.id, User.username, User.display_name, Platform.name)
        )

        total = query.count()

        # 4. Deterministic sorting on SQL aggregates
        sort_col_map = {
            "post_count": post_count_col,
            "total_likes": total_likes_col,
            "total_comments": total_comments_col,
            "total_shares": total_shares_col,
            "total_views": total_views_col,
        }

        is_desc = (clean_order == "desc")
        primary_agg = sort_col_map[clean_sort_by]
        primary_clause = primary_agg.desc() if is_desc else primary_agg.asc()

        if clean_sort_by == "post_count":
            secondary_clause = total_likes_col.desc() if is_desc else total_likes_col.asc()
        else:
            secondary_clause = post_count_col.desc() if is_desc else post_count_col.asc()

        tie_breaker_name = User.username.desc() if is_desc else User.username.asc()
        tie_breaker_id = User.id.desc() if is_desc else User.id.asc()

        order_by_clauses = [primary_clause, secondary_clause, tie_breaker_name, tie_breaker_id]

        rows = (
            query.order_by(*order_by_clauses)
            .offset(offset)
            .limit(limit)
            .all()
        )

        items: List[AuthorSummary] = []
        for row in rows:
            post_count = int(row.post_count) if row.post_count else 0
            total_likes = int(row.total_likes) if row.total_likes else 0
            total_comments = int(row.total_comments) if row.total_comments else 0
            total_shares = int(row.total_shares) if row.total_shares else 0
            total_views = int(row.total_views) if row.total_views else 0

            divisor = float(post_count) if post_count > 0 else 1.0
            avg_likes = round(total_likes / divisor, 2)
            avg_comments = round(total_comments / divisor, 2)
            avg_shares = round(total_shares / divisor, 2)
            avg_views = round(total_views / divisor, 2)

            items.append(
                AuthorSummary(
                    username=row.username,
                    display_name=row.display_name,
                    platform=row.platform,
                    post_count=post_count,
                    total_likes=total_likes,
                    total_comments=total_comments,
                    total_shares=total_shares,
                    total_views=total_views,
                    avg_likes=avg_likes,
                    avg_comments=avg_comments,
                    avg_shares=avg_shares,
                    avg_views=avg_views,
                    earliest_post=row.earliest_post,
                    latest_post=row.latest_post,
                )
            )

        return AuthorListResponse(total=total, limit=limit, offset=offset, items=items)
