import math
import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from app.schemas.analytics_engine import (
    DetailedTrendReport,
    PlatformTrendSummary,
    TrendItemProfile,
    TrendMomentumMetrics,
)
from app.services.analytics_engine.base import BaseTrendAnalyticsEngine
from app.services.analytics_engine.engagement import (
    EngagementEngine,
    extract_post_id_safe,
    extract_post_metrics,
)
from app.services.analytics_engine.narrative import (
    extract_post_topic_association,
)
from app.services.analytics_engine.time_series import (
    extract_post_timestamp,
)


def extract_hashtags_and_keywords(text: str) -> Tuple[List[str], List[str]]:
    """Extract hashtags and prominent terms from text content."""
    if not text:
        return [], []

    hashtags = [h.lower() for h in re.findall(r"#\w+", text)]
    # Extract clean words > 3 chars
    clean_words = [
        w.lower() for w in re.findall(r"\b[a-zA-Z]{4,}\b", text)
        if w.lower() not in {"this", "that", "with", "from", "have", "more", "will", "about", "there", "their"}
    ]
    return hashtags, clean_words


class TrendAnalyticsEngine(BaseTrendAnalyticsEngine):
    """
    Modular Trend Detection & Momentum Engine for Phase 4.4.
    Identifies topics, hashtags, and keywords gaining or losing momentum,
    distinguishing true momentum from raw baseline popularity.
    """

    def __init__(self, engagement_engine: Optional[EngagementEngine] = None) -> None:
        self.engagement_engine = engagement_engine or EngagementEngine()

    def calculate_trend_momentum(
        self,
        current_volume: int,
        baseline_volume: int,
        current_engagement: float = 0.0,
        baseline_engagement: float = 0.0,
        z_score: float = 0.0,
    ) -> TrendMomentumMetrics:
        """
        Calculate mathematical momentum metrics, distinct from static volume counts.
        """
        if current_volume == 0 and baseline_volume == 0:
            return TrendMomentumMetrics(
                current_volume=0,
                baseline_volume=0,
                growth_rate_pct=0.0,
                velocity=0.0,
                acceleration=0.0,
                momentum_score=0.0,
                z_score=0.0,
                direction="stable",
            )

        velocity = float(current_volume - baseline_volume)
        acceleration = float(velocity - baseline_volume) if baseline_volume > 0 else float(velocity)

        # Growth rate %
        if baseline_volume > 0:
            growth_rate_pct = round(((current_volume - baseline_volume) / baseline_volume) * 100.0, 2)
        else:
            growth_rate_pct = float(current_volume * 100.0)

        # Engagement amplification factor
        avg_post_eng = current_engagement / max(current_volume, 1)
        engagement_factor = 1.0 + min(2.0, avg_post_eng / 100.0)

        # Growth multiplier
        growth_multiplier = math.log2(2.0 + max(0.0, growth_rate_pct) / 100.0)

        # Determine direction and momentum
        is_emerging = (baseline_volume == 0 and current_volume > 0)
        is_spiking = (z_score >= 2.0 or (growth_rate_pct >= 200.0 and current_volume >= 3))

        if is_spiking:
            direction = "spiking"
            momentum = round(float(current_volume) * 2.5 * growth_multiplier * engagement_factor, 4)
        elif is_emerging:
            direction = "emerging"
            momentum = round(float(current_volume) * 2.0 * engagement_factor, 4)
        elif velocity > 0 and acceleration > 0:
            direction = "accelerating"
            momentum = round(velocity * growth_multiplier * engagement_factor, 4)
        elif velocity < 0:
            direction = "declining"
            momentum = round(velocity * (1.0 / max(1.0, engagement_factor)), 4)
        else:
            direction = "stable"
            momentum = round(max(0.1, float(current_volume) * 0.1), 4)

        return TrendMomentumMetrics(
            current_volume=current_volume,
            baseline_volume=baseline_volume,
            growth_rate_pct=growth_rate_pct,
            velocity=round(velocity, 4),
            acceleration=round(acceleration, 4),
            momentum_score=momentum,
            z_score=round(z_score, 2),
            direction=direction,
        )

    def analyze_trends(
        self,
        posts: List[Any],
        topics: Optional[List[Any]] = None,
        reference_time: Optional[datetime] = None,
        split_ratio: float = 0.5,
    ) -> List[TrendItemProfile]:
        """
        Analyze multi-dimensional trends across hashtags, topics, and prominent keywords.
        """
        if not posts:
            return []

        # 1. Group posts by entity
        entity_posts_map: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"item_type": "keyword", "display_name": "", "posts": []}
        )

        # Track explicit topic models if provided
        if topics:
            for t in topics:
                if isinstance(t, dict):
                    t_id = str(t.get("topic_id") or t.get("id") or "topic_0")
                    t_label = str(t.get("label") or t.get("name") or t_id)
                    p_ids = set(str(pid) for pid in (t.get("post_ids") or []))
                    ext_p_ids = set(str(pid) for pid in (t.get("external_post_ids") or []))
                else:
                    t_id = str(getattr(t, "topic_id", None) or getattr(t, "id", None) or "topic_0")
                    t_label = str(getattr(t, "label", None) or getattr(t, "name", None) or t_id)
                    p_ids = set(str(pid) for pid in (getattr(t, "post_ids", None) or []))
                    ext_p_ids = set(str(pid) for pid in (getattr(t, "external_post_ids", None) or []))

                all_ids = p_ids.union(ext_p_ids)
                entity_posts_map[t_id] = {
                    "item_type": "topic",
                    "display_name": t_label,
                    "target_ids": all_ids,
                    "posts": [],
                }

        # Inspect posts
        for idx, post in enumerate(posts):
            p_id = extract_post_id_safe(post, idx)
            text = ""
            if isinstance(post, dict):
                text = str(post.get("text") or post.get("content") or "")
            else:
                text = str(getattr(post, "text", None) or getattr(post, "content", None) or "")

            # Match explicit topics
            matched_topic = False
            if topics:
                for t_id, meta in entity_posts_map.items():
                    if meta.get("item_type") == "topic" and p_id in meta.get("target_ids", set()):
                        meta["posts"].append((idx, post))
                        matched_topic = True

            # Match inferred topic
            if not matched_topic:
                t_id, t_label, _ = extract_post_topic_association(post)
                if t_id and t_id != "general":
                    entity_posts_map[t_id]["item_type"] = "topic"
                    entity_posts_map[t_id]["display_name"] = t_label or t_id
                    entity_posts_map[t_id]["posts"].append((idx, post))

            # Match hashtags
            hashtags, keywords = extract_hashtags_and_keywords(text)
            for ht in hashtags:
                entity_posts_map[ht]["item_type"] = "hashtag"
                entity_posts_map[ht]["display_name"] = ht
                entity_posts_map[ht]["posts"].append((idx, post))

            for kw in keywords[:3]:
                entity_posts_map[kw]["item_type"] = "keyword"
                entity_posts_map[kw]["display_name"] = kw.capitalize()
                entity_posts_map[kw]["posts"].append((idx, post))

        # Determine reference window and midpoint
        timestamps: List[datetime] = []
        for post in posts:
            ts = extract_post_timestamp(post)
            if ts:
                timestamps.append(ts)

        if timestamps:
            min_ts = min(timestamps)
            max_ts = reference_time or max(timestamps)
            if min_ts == max_ts:
                midpoint_ts = min_ts
            else:
                midpoint_ts = min_ts + (max_ts - min_ts) * split_ratio
        else:
            midpoint_ts = None

        trend_profiles: List[TrendItemProfile] = []

        for entity_id, meta in entity_posts_map.items():
            entry_posts = meta["posts"]
            if not entry_posts:
                continue

            # Deduplicate multiple occurrences of same post for single entity
            seen_post_indices = set()
            unique_entries = []
            for i, p in entry_posts:
                if i not in seen_post_indices:
                    seen_post_indices.add(i)
                    unique_entries.append((i, p))

            total_count = len(unique_entries)
            sample_ids = [extract_post_id_safe(p, i) for i, p in unique_entries[:5]]
            platforms = list(sorted(set(extract_post_metrics(p)[4] for _, p in unique_entries)))

            # Partition into baseline vs current
            prev_posts: List[Any] = []
            curr_posts: List[Any] = []

            for _, p in unique_entries:
                ts = extract_post_timestamp(p)
                if ts and midpoint_ts:
                    if ts < midpoint_ts:
                        prev_posts.append(p)
                    else:
                        curr_posts.append(p)
                else:
                    curr_posts.append(p)

            if not midpoint_ts and total_count > 1:
                split_idx = int(total_count * (1.0 - split_ratio))
                prev_posts = [p for _, p in unique_entries[:split_idx]]
                curr_posts = [p for _, p in unique_entries[split_idx:]]

            curr_vol = len(curr_posts)
            base_vol = len(prev_posts)

            curr_eng = self.engagement_engine.calculate_engagement(curr_posts).weighted_engagement_score
            base_eng = self.engagement_engine.calculate_engagement(prev_posts).weighted_engagement_score

            # Calculate simple z-score heuristic
            mean_v = (curr_vol + base_vol) / 2.0
            std_v = math.sqrt(((curr_vol - mean_v) ** 2 + (base_vol - mean_v) ** 2) / 2.0)
            z_val = ((curr_vol - mean_v) / std_v) if std_v > 0 else 0.0

            momentum_metrics = self.calculate_trend_momentum(
                current_volume=curr_vol,
                baseline_volume=base_vol,
                current_engagement=curr_eng,
                baseline_engagement=base_eng,
                z_score=z_val,
            )

            trend_profiles.append(
                TrendItemProfile(
                    trend_id=entity_id,
                    name=meta.get("display_name") or entity_id,
                    item_type=meta.get("item_type") or "topic",
                    post_count=total_count,
                    momentum=momentum_metrics,
                    sample_post_ids=sample_ids,
                    is_emerging=(momentum_metrics.direction == "emerging"),
                    is_spiking=(momentum_metrics.direction == "spiking"),
                    platforms=platforms,
                )
            )

        # Sort trends by momentum score descending
        trend_profiles.sort(key=lambda t: t.momentum.momentum_score, reverse=True)
        return trend_profiles

    def calculate_platform_trends(
        self, posts: List[Any], top_limit: int = 5
    ) -> Dict[str, PlatformTrendSummary]:
        """Calculate trend rankings partitioned by platform."""
        if not posts:
            return {}

        platform_groups: Dict[str, List[Any]] = defaultdict(list)
        for post in posts:
            _, _, _, _, platform = extract_post_metrics(post)
            platform_groups[platform].append(post)

        summaries: Dict[str, PlatformTrendSummary] = {}
        for platform_name, plat_posts in sorted(platform_groups.items()):
            plat_trends = self.analyze_trends(plat_posts)
            spiking_count = sum(1 for t in plat_trends if t.is_spiking)
            emerging_count = sum(1 for t in plat_trends if t.is_emerging)

            summaries[platform_name] = PlatformTrendSummary(
                platform=platform_name,
                top_trends=plat_trends[:top_limit],
                spiking_trends_count=spiking_count,
                emerging_trends_count=emerging_count,
            )

        return summaries

    def generate_detailed_report(
        self,
        posts: List[Any],
        topics: Optional[List[Any]] = None,
        top_limit: int = 10,
        reference_time: Optional[datetime] = None,
    ) -> DetailedTrendReport:
        """Generate comprehensive Phase 4.4 Trend Analytics report."""
        ranked_trends = self.analyze_trends(posts, topics=topics, reference_time=reference_time)
        platform_trends = self.calculate_platform_trends(posts, top_limit=top_limit)

        emerging = [t for t in ranked_trends if t.is_emerging]
        spiking = [t for t in ranked_trends if t.is_spiking]
        accelerating = [t for t in ranked_trends if t.momentum.direction == "accelerating"]
        stable = [t for t in ranked_trends if t.momentum.direction == "stable"]
        declining = [t for t in ranked_trends if t.momentum.direction == "declining"]

        return DetailedTrendReport(
            total_trends_evaluated=len(ranked_trends),
            emerging_count=len(emerging),
            accelerating_count=len(accelerating),
            spiking_count=len(spiking),
            stable_count=len(stable),
            declining_count=len(declining),
            ranked_trends=ranked_trends[:top_limit],
            platform_trends=platform_trends,
            top_spiking_trends=spiking[:top_limit],
            top_emerging_trends=emerging[:top_limit],
        )
