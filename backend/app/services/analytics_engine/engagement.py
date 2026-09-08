from typing import Any, Dict, List, Tuple
from collections import defaultdict

from app.schemas.analytics_engine import EngagementScoreBreakdown
from app.services.analytics_engine.base import BaseEngagementEngine


def extract_post_metrics(post: Any) -> Tuple[int, int, int, int, str]:
    """
    Extract (likes, comments, shares, views, platform) safely across various post models.
    Supports AnalyticsReadyPost, NormalizedPost, PostSummary, Post ORM, or dictionary representations.
    """
    likes = 0
    comments = 0
    shares = 0
    views = 0
    platform = "unknown"

    if isinstance(post, dict):
        platform = str(post.get("platform") or "unknown").lower()
        metrics = post.get("metrics")
        if isinstance(metrics, dict):
            likes = int(metrics.get("likes") or 0)
            comments = int(metrics.get("comments") or 0)
            shares = int(metrics.get("shares") or 0)
            views = int(metrics.get("views") or 0)
        else:
            likes = int(post.get("likes") or 0)
            comments = int(post.get("comments") or 0)
            shares = int(post.get("shares") or 0)
            views = int(post.get("views") or 0)
    else:
        # Pydantic or ORM object
        platform = str(getattr(post, "platform", "unknown") or "unknown").lower()
        metrics = getattr(post, "metrics", None)
        if metrics is not None:
            if isinstance(metrics, dict):
                likes = int(metrics.get("likes") or 0)
                comments = int(metrics.get("comments") or 0)
                shares = int(metrics.get("shares") or 0)
                views = int(metrics.get("views") or 0)
            else:
                likes = int(getattr(metrics, "likes", 0) or 0)
                comments = int(getattr(metrics, "comments", 0) or 0)
                shares = int(getattr(metrics, "shares", 0) or 0)
                views = int(getattr(metrics, "views", 0) or 0)
        else:
            likes = int(getattr(post, "likes", 0) or 0)
            comments = int(getattr(post, "comments", 0) or 0)
            shares = int(getattr(post, "shares", 0) or 0)
            views = int(getattr(post, "views", 0) or 0)

    return max(0, likes), max(0, comments), max(0, shares), max(0, views), platform


class EngagementEngine(BaseEngagementEngine):
    """
    Deterministic engagement and virality computation engine.
    Calculates weighted multi-signal engagement scores, virality ratios, and discussion depths.
    """

    def __init__(
        self,
        weight_like: float = 1.0,
        weight_comment: float = 2.0,
        weight_share: float = 3.0,
    ) -> None:
        self.weight_like = weight_like
        self.weight_comment = weight_comment
        self.weight_share = weight_share

    def calculate_post_weighted_score(self, likes: int, comments: int, shares: int) -> float:
        """Calculate weighted score for an individual post or interval."""
        return round(
            (likes * self.weight_like) + (comments * self.weight_comment) + (shares * self.weight_share),
            4,
        )

    def calculate_engagement(self, posts: List[Any]) -> EngagementScoreBreakdown:
        """Calculate aggregate engagement breakdown across a collection of posts."""
        if not posts:
            return EngagementScoreBreakdown(
                total_posts=0,
                total_likes=0,
                total_comments=0,
                total_shares=0,
                total_views=0,
                weighted_engagement_score=0.0,
                virality_index=0.0,
                discussion_depth=0.0,
                engagement_rate_per_impression=0.0,
                average_post_engagement=0.0,
            )

        total_posts = len(posts)
        total_likes = 0
        total_comments = 0
        total_shares = 0
        total_views = 0

        for post in posts:
            l, c, s, v, _ = extract_post_metrics(post)
            total_likes += l
            total_comments += c
            total_shares += s
            total_views += v

        weighted_score = self.calculate_post_weighted_score(total_likes, total_comments, total_shares)
        
        # Virality Index: ratio of shares to likes (or baseline 1 if 0 likes)
        virality_index = round(total_shares / max(total_likes, 1), 4)
        
        # Discussion Depth: ratio of comments to likes
        discussion_depth = round(total_comments / max(total_likes, 1), 4)
        
        # Engagement Rate per Impression: interactions / views
        if total_views > 0:
            total_interactions = total_likes + total_comments + total_shares
            engagement_rate = round(total_interactions / total_views, 6)
        else:
            engagement_rate = 0.0

        avg_post_eng = round(weighted_score / total_posts, 4) if total_posts > 0 else 0.0

        return EngagementScoreBreakdown(
            total_posts=total_posts,
            total_likes=total_likes,
            total_comments=total_comments,
            total_shares=total_shares,
            total_views=total_views,
            weighted_engagement_score=weighted_score,
            virality_index=virality_index,
            discussion_depth=discussion_depth,
            engagement_rate_per_impression=engagement_rate,
            average_post_engagement=avg_post_eng,
        )

    def calculate_platform_breakdown(self, posts: List[Any]) -> Dict[str, EngagementScoreBreakdown]:
        """Calculate engagement statistics partitioned by platform."""
        if not posts:
            return {}

        platform_groups: Dict[str, List[Any]] = defaultdict(list)
        for post in posts:
            _, _, _, _, platform = extract_post_metrics(post)
            platform_groups[platform].append(post)

        return {
            platform: self.calculate_engagement(plat_posts)
            for platform, plat_posts in sorted(platform_groups.items())
        }
