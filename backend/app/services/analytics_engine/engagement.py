import math
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from app.schemas.analytics_engine import (
    DetailedEngagementReport,
    DiscussionDepthAnalytics,
    EngagementDistribution,
    EngagementScoreBreakdown,
    PlatformComparativeReport,
    PlatformEngagementComparison,
    PostEngagementProfile,
    ViralityAnalytics,
)
from app.services.analytics_engine.base import BaseEngagementEngine


def extract_post_id_safe(post: Any, index: int) -> str:
    """Extract post ID safely from various object models or fallback to index."""
    if isinstance(post, dict):
        return str(post.get("id") or post.get("external_post_id") or post.get("external_id") or f"post_{index}")
    return str(
        getattr(post, "id", None)
        or getattr(post, "external_post_id", None)
        or getattr(post, "external_id", None)
        or f"post_{index}"
    )


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


def calculate_percentile(sorted_data: List[float], percentile: float) -> float:
    """Calculate percentile from a sorted list of numeric values."""
    if not sorted_data:
        return 0.0
    if len(sorted_data) == 1:
        return sorted_data[0]
    k = (len(sorted_data) - 1) * percentile
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_data[int(k)]
    d0 = sorted_data[f] * (c - k)
    d1 = sorted_data[c] * (k - f)
    return round(d0 + d1, 4)


class EngagementEngine(BaseEngagementEngine):
    """
    Deterministic engagement and virality computation engine (Phase 4.2).
    Calculates weighted multi-signal engagement scores, virality ratios, discussion depths,
    statistical distributions, outlier detection, and comparative platform benchmarks.
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

    def calculate_distribution(self, posts: List[Any]) -> EngagementDistribution:
        """Calculate statistical distribution of engagement scores across posts."""
        if not posts:
            return EngagementDistribution(
                min_engagement=0.0,
                max_engagement=0.0,
                mean_engagement=0.0,
                median_engagement=0.0,
                std_dev_engagement=0.0,
                p25=0.0,
                p75=0.0,
            )

        scores: List[float] = []
        for post in posts:
            l, c, s, _, _ = extract_post_metrics(post)
            scores.append(self.calculate_post_weighted_score(l, c, s))

        scores.sort()
        n = len(scores)
        min_val = scores[0]
        max_val = scores[-1]
        mean_val = round(sum(scores) / n, 4)

        # Median
        if n % 2 == 1:
            median_val = scores[n // 2]
        else:
            median_val = round((scores[(n // 2) - 1] + scores[n // 2]) / 2.0, 4)

        # Standard deviation
        variance = sum((x - mean_val) ** 2 for x in scores) / n if n > 0 else 0.0
        std_dev = round(math.sqrt(variance), 4)

        p25 = calculate_percentile(scores, 0.25)
        p75 = calculate_percentile(scores, 0.75)

        return EngagementDistribution(
            min_engagement=round(min_val, 4),
            max_engagement=round(max_val, 4),
            mean_engagement=mean_val,
            median_engagement=round(median_val, 4),
            std_dev_engagement=std_dev,
            p25=p25,
            p75=p75,
        )

    def calculate_virality_analytics(
        self, posts: List[Any], high_virality_threshold: float = 0.5
    ) -> ViralityAnalytics:
        """Calculate virality index, amplification rate, and count of highly viral posts."""
        if not posts:
            return ViralityAnalytics(
                virality_index=0.0,
                amplification_rate=0.0,
                shares_per_post=0.0,
                high_virality_posts_count=0,
            )

        total_likes = 0
        total_comments = 0
        total_shares = 0
        high_viral_count = 0

        for post in posts:
            l, c, s, _, _ = extract_post_metrics(post)
            total_likes += l
            total_comments += c
            total_shares += s
            post_v_ratio = s / max(l, 1)
            if post_v_ratio >= high_virality_threshold:
                high_viral_count += 1

        total_interactions = total_likes + total_comments + total_shares
        virality_idx = round(total_shares / max(total_likes, 1), 4)
        amplification_rate = round(total_shares / max(total_interactions, 1), 4) if total_interactions > 0 else 0.0
        shares_per_post = round(total_shares / len(posts), 4)

        return ViralityAnalytics(
            virality_index=virality_idx,
            amplification_rate=amplification_rate,
            shares_per_post=shares_per_post,
            high_virality_posts_count=high_viral_count,
        )

    def calculate_discussion_analytics(
        self, posts: List[Any], high_discussion_threshold: float = 0.5
    ) -> DiscussionDepthAnalytics:
        """Calculate discussion depth, conversation rate, and count of active discussion threads."""
        if not posts:
            return DiscussionDepthAnalytics(
                discussion_depth=0.0,
                conversation_rate=0.0,
                comments_per_post=0.0,
                high_discussion_posts_count=0,
            )

        total_likes = 0
        total_comments = 0
        total_shares = 0
        high_disc_count = 0

        for post in posts:
            l, c, s, _, _ = extract_post_metrics(post)
            total_likes += l
            total_comments += c
            total_shares += s
            post_d_ratio = c / max(l, 1)
            if post_d_ratio >= high_discussion_threshold:
                high_disc_count += 1

        total_interactions = total_likes + total_comments + total_shares
        discussion_depth = round(total_comments / max(total_likes, 1), 4)
        conversation_rate = round(total_comments / max(total_interactions, 1), 4) if total_interactions > 0 else 0.0
        comments_per_post = round(total_comments / len(posts), 4)

        return DiscussionDepthAnalytics(
            discussion_depth=discussion_depth,
            conversation_rate=conversation_rate,
            comments_per_post=comments_per_post,
            high_discussion_posts_count=high_disc_count,
        )

    def extract_top_posts(
        self, posts: List[Any], limit: int = 10, outlier_sigma: float = 2.0
    ) -> Tuple[List[PostEngagementProfile], List[PostEngagementProfile]]:
        """Extract top engaging posts and identify statistically high engagement outliers."""
        if not posts:
            return [], []

        profiles: List[PostEngagementProfile] = []
        for idx, post in enumerate(posts):
            p_id = extract_post_id_safe(post, idx)
            l, c, s, v, platform = extract_post_metrics(post)
            weighted_score = self.calculate_post_weighted_score(l, c, s)
            virality_score = round(s / max(l, 1), 4)
            discussion_depth = round(c / max(l, 1), 4)
            eng_rate = round((l + c + s) / v, 6) if v > 0 else 0.0

            profiles.append(
                PostEngagementProfile(
                    post_id=p_id,
                    platform=platform,
                    likes=l,
                    comments=c,
                    shares=s,
                    views=v,
                    weighted_score=weighted_score,
                    virality_score=virality_score,
                    discussion_depth=discussion_depth,
                    engagement_rate=eng_rate,
                    is_outlier=False,
                )
            )

        # Outlier calculation
        scores = [p.weighted_score for p in profiles]
        mean_score = sum(scores) / len(scores) if scores else 0.0
        variance = sum((x - mean_score) ** 2 for x in scores) / len(scores) if len(scores) > 1 else 0.0
        std_dev = math.sqrt(variance)

        outliers: List[PostEngagementProfile] = []
        if std_dev > 0:
            outlier_threshold = mean_score + (outlier_sigma * std_dev)
            for p in profiles:
                if p.weighted_score >= outlier_threshold and p.weighted_score > mean_score:
                    p.is_outlier = True
                    outliers.append(p)

        # Sort descending by weighted score
        profiles.sort(key=lambda p: p.weighted_score, reverse=True)
        outliers.sort(key=lambda p: p.weighted_score, reverse=True)

        return profiles[:limit], outliers

    def calculate_platform_comparison(self, posts: List[Any]) -> PlatformComparativeReport:
        """Calculate cross-platform comparative benchmarks, shares, and efficiency rankings."""
        if not posts:
            return PlatformComparativeReport(
                platforms={},
                top_volume_platform=None,
                top_engaging_platform=None,
                top_viral_platform=None,
                top_discussion_platform=None,
            )

        total_posts_count = len(posts)
        platform_groups: Dict[str, List[Any]] = defaultdict(list)
        for post in posts:
            _, _, _, _, platform = extract_post_metrics(post)
            platform_groups[platform].append(post)

        # Total network engagement score
        network_engagement_score = 0.0
        for post in posts:
            l, c, s, _, _ = extract_post_metrics(post)
            network_engagement_score += self.calculate_post_weighted_score(l, c, s)

        platform_comps: Dict[str, PlatformEngagementComparison] = {}
        for plat_name, plat_posts in platform_groups.items():
            breakdown = self.calculate_engagement(plat_posts)
            post_share = round((breakdown.total_posts / total_posts_count) * 100.0, 2)
            eng_share = (
                round((breakdown.weighted_engagement_score / network_engagement_score) * 100.0, 2)
                if network_engagement_score > 0
                else 0.0
            )

            platform_comps[plat_name] = PlatformEngagementComparison(
                platform=plat_name,
                total_posts=breakdown.total_posts,
                post_share_pct=post_share,
                engagement_share_pct=eng_share,
                weighted_engagement_score=breakdown.weighted_engagement_score,
                avg_engagement_per_post=breakdown.average_post_engagement,
                virality_index=breakdown.virality_index,
                discussion_depth=breakdown.discussion_depth,
                engagement_rate_per_impression=breakdown.engagement_rate_per_impression,
                efficiency_rank=1,
            )

        # Assign efficiency ranks based on avg_engagement_per_post descending
        sorted_by_efficiency = sorted(
            platform_comps.values(), key=lambda p: p.avg_engagement_per_post, reverse=True
        )
        for rank, comp in enumerate(sorted_by_efficiency, start=1):
            comp.efficiency_rank = rank

        # Determine leaders
        top_volume = max(platform_comps.values(), key=lambda p: p.total_posts).platform if platform_comps else None
        top_engaging = (
            max(platform_comps.values(), key=lambda p: p.weighted_engagement_score).platform
            if platform_comps
            else None
        )
        top_viral = max(platform_comps.values(), key=lambda p: p.virality_index).platform if platform_comps else None
        top_discussion = (
            max(platform_comps.values(), key=lambda p: p.discussion_depth).platform if platform_comps else None
        )

        return PlatformComparativeReport(
            platforms=platform_comps,
            top_volume_platform=top_volume,
            top_engaging_platform=top_engaging,
            top_viral_platform=top_viral,
            top_discussion_platform=top_discussion,
        )

    def generate_detailed_report(
        self, posts: List[Any], top_limit: int = 10, outlier_sigma: float = 2.0
    ) -> DetailedEngagementReport:
        """Generate comprehensive Phase 4.2 multi-dimensional engagement analysis report."""
        overall = self.calculate_engagement(posts)
        distribution = self.calculate_distribution(posts)
        virality = self.calculate_virality_analytics(posts)
        discussion = self.calculate_discussion_analytics(posts)
        platform_comparison = self.calculate_platform_comparison(posts)
        top_posts, outliers = self.extract_top_posts(posts, limit=top_limit, outlier_sigma=outlier_sigma)

        return DetailedEngagementReport(
            overall=overall,
            distribution=distribution,
            virality=virality,
            discussion=discussion,
            platform_comparison=platform_comparison,
            top_posts=top_posts,
            outliers=outliers,
        )
