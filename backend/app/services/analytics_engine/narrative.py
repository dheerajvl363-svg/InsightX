from datetime import datetime, timezone
from typing import Any, Counter, Dict, List, Optional, Tuple
from collections import Counter as Occurrences, defaultdict

from app.schemas.analytics_engine import (
    NarrativeIntelligence,
    NarrativeLifecycleStage,
    NarrativeTrajectoryMetrics,
)
from app.services.analytics_engine.base import BaseNarrativeEngine
from app.services.analytics_engine.engagement import EngagementEngine, extract_post_metrics
from app.services.analytics_engine.time_series import (
    extract_post_sentiment_and_emotion,
    extract_post_timestamp,
)


def extract_post_id(post: Any, index: int) -> str:
    """Extract unique post ID from any supported post representation."""
    if isinstance(post, dict):
        return str(post.get("id") or post.get("external_post_id") or post.get("external_id") or f"post_{index}")
    return str(
        getattr(post, "id", None)
        or getattr(post, "external_post_id", None)
        or getattr(post, "external_id", None)
        or f"post_{index}"
    )


def extract_post_topic_association(post: Any) -> Tuple[Optional[str], Optional[str], List[str]]:
    """
    Extract topic ID, topic label, and keywords from a post.
    Checks direct attributes, metadata, or topic annotations.
    """
    topic_id = None
    label = None
    keywords: List[str] = []

    if isinstance(post, dict):
        topic_id = post.get("topic_id") or post.get("cluster_id")
        label = post.get("topic_label") or post.get("topic")
        kws = post.get("keywords") or post.get("hashtags")
        if isinstance(kws, list):
            keywords = [str(k) for k in kws]
    else:
        topic_id = getattr(post, "topic_id", None) or getattr(post, "cluster_id", None)
        label = getattr(post, "topic_label", None) or getattr(post, "topic", None)
        kws = getattr(post, "keywords", None) or getattr(post, "hashtags", None)
        if isinstance(kws, list):
            keywords = [str(k) for k in kws]

        # Metadata inspection
        meta = getattr(post, "metadata", None)
        if isinstance(meta, dict):
            if not topic_id:
                topic_id = meta.get("topic_id") or meta.get("cluster_id")
            if not label:
                label = meta.get("topic_label") or meta.get("topic")
            if not keywords and ("keywords" in meta or "hashtags" in meta):
                kws = meta.get("keywords") or meta.get("hashtags")
                if isinstance(kws, list):
                    keywords = [str(k) for k in kws]

    if label and not topic_id:
        topic_id = label.lower().replace(" ", "_")
    elif topic_id and not label:
        label = topic_id.replace("_", " ").title()

    return topic_id, label, keywords


class NarrativeDynamicsEngine(BaseNarrativeEngine):
    """
    Narrative lifecycle and trajectory dynamics engine.
    Classifies narrative stages, velocity, acceleration, and cross-temporal sentiment drift.
    """

    def __init__(self, engagement_engine: Optional[EngagementEngine] = None) -> None:
        self.engagement_engine = engagement_engine or EngagementEngine()

    def classify_lifecycle_stage(
        self,
        current_volume: int,
        previous_volume: int,
        velocity: float,
        acceleration: float,
    ) -> NarrativeLifecycleStage:
        """
        Classify lifecycle stage based on temporal volume trajectory.
        """
        if current_volume == 0 and previous_volume == 0:
            return NarrativeLifecycleStage.DORMANT

        if previous_volume == 0 and current_volume > 0:
            return NarrativeLifecycleStage.EMERGING

        if current_volume == 0 and previous_volume > 0:
            return NarrativeLifecycleStage.DORMANT

        # Both periods have positive volume
        if velocity > 0 and acceleration > 0:
            return NarrativeLifecycleStage.ACCELERATING
        elif velocity > 0 and acceleration <= 0:
            return NarrativeLifecycleStage.PEAK
        elif velocity == 0 or (abs(velocity) <= max(1, previous_volume * 0.15) and current_volume >= 3):
            return NarrativeLifecycleStage.SUSTAINED
        elif velocity < 0:
            return NarrativeLifecycleStage.DECAYING

        return NarrativeLifecycleStage.SUSTAINED

    def analyze_narratives(
        self,
        posts: List[Any],
        topics: Optional[List[Any]] = None,
        reference_time: Optional[datetime] = None,
        split_ratio: float = 0.5,
    ) -> List[NarrativeIntelligence]:
        """
        Analyze narrative trajectories across supplied posts and topic clusters.
        """
        if not posts:
            return []

        # Build topic-to-posts mapping
        topic_posts_map: Dict[str, List[Tuple[int, Any]]] = defaultdict(list)
        topic_metadata: Dict[str, Dict[str, Any]] = {}

        # If explicit topic models were provided (e.g. from Phase 3.4 TopicEngine)
        if topics:
            for t in topics:
                if isinstance(t, dict):
                    t_id = str(t.get("topic_id") or t.get("cluster_id") or t.get("id") or "topic_0")
                    t_label = str(t.get("label") or t.get("name") or t_id)
                    t_kws = list(t.get("keywords") or [])
                    p_ids = [str(pid) for pid in (t.get("post_ids") or [])]
                    ext_p_ids = [str(pid) for pid in (t.get("external_post_ids") or [])]
                    post_ids = set(p_ids + ext_p_ids)
                else:
                    t_id = str(getattr(t, "topic_id", None) or getattr(t, "cluster_id", None) or getattr(t, "id", None) or "topic_0")
                    t_label = str(getattr(t, "label", None) or getattr(t, "name", None) or t_id)
                    t_kws = list(getattr(t, "keywords", None) or [])
                    p_ids = [str(pid) for pid in (getattr(t, "post_ids", None) or [])]
                    ext_p_ids = [str(pid) for pid in (getattr(t, "external_post_ids", None) or [])]
                    post_ids = set(p_ids + ext_p_ids)

                topic_metadata[t_id] = {
                    "label": t_label,
                    "keywords": t_kws,
                    "target_post_ids": post_ids,
                }

        # Associate posts with topics
        for idx, post in enumerate(posts):
            p_id = extract_post_id(post, idx)
            matched = False

            # Check explicit topic mapping
            if topics:
                for t_id, t_meta in topic_metadata.items():
                    if p_id in t_meta["target_post_ids"]:
                        topic_posts_map[t_id].append((idx, post))
                        matched = True

            if not matched:
                t_id, t_label, t_kws = extract_post_topic_association(post)
                if t_id:
                    if t_id not in topic_metadata:
                        topic_metadata[t_id] = {
                            "label": t_label or f"Topic {t_id}",
                            "keywords": t_kws,
                            "target_post_ids": set(),
                        }
                    topic_posts_map[t_id].append((idx, post))
                else:
                    # Fallback general narrative
                    fallback_id = "general"
                    if fallback_id not in topic_metadata:
                        topic_metadata[fallback_id] = {
                            "label": "General Discussion",
                            "keywords": [],
                            "target_post_ids": set(),
                        }
                    topic_posts_map[fallback_id].append((idx, post))

        # Determine reference time and split threshold
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
                total_span = (max_ts - min_ts).total_seconds()
                midpoint_ts = min_ts + (max_ts - min_ts) * split_ratio
        else:
            midpoint_ts = None

        results: List[NarrativeIntelligence] = []

        for t_id, post_entries in sorted(topic_posts_map.items()):
            meta = topic_metadata.get(t_id, {"label": t_id, "keywords": []})
            topic_posts = [p for _, p in post_entries]
            sample_ids = [extract_post_id(p, i) for i, p in post_entries[:5]]

            # Split posts into previous vs current period
            prev_posts: List[Any] = []
            curr_posts: List[Any] = []
            topic_timestamps: List[datetime] = []

            for p in topic_posts:
                ts = extract_post_timestamp(p)
                if ts:
                    topic_timestamps.append(ts)
                    if midpoint_ts:
                        if ts < midpoint_ts:
                            prev_posts.append(p)
                        else:
                            curr_posts.append(p)
                    else:
                        curr_posts.append(p)
                else:
                    # Without timestamps, split evenly based on array index
                    curr_posts.append(p)

            if not midpoint_ts and len(topic_posts) > 1:
                split_idx = int(len(topic_posts) * (1.0 - split_ratio))
                prev_posts = topic_posts[:split_idx]
                curr_posts = topic_posts[split_idx:]

            prev_vol = len(prev_posts)
            curr_vol = len(curr_posts)

            # Velocity and acceleration
            volume_velocity = round(float(curr_vol - prev_vol), 4)
            volume_acceleration = round(volume_velocity - (prev_vol if prev_vol > 0 else 0), 4)

            # Engagement velocity
            prev_eng = self.engagement_engine.calculate_engagement(prev_posts).weighted_engagement_score
            curr_eng = self.engagement_engine.calculate_engagement(curr_posts).weighted_engagement_score
            eng_velocity = round(curr_eng - prev_eng, 4)

            # Sentiment drift
            prev_pols = [
                pol for p in prev_posts
                for pol, _, _ in [extract_post_sentiment_and_emotion(p)]
                if pol is not None
            ]
            curr_pols = [
                pol for p in curr_posts
                for pol, _, _ in [extract_post_sentiment_and_emotion(p)]
                if pol is not None
            ]
            mean_prev_pol = sum(prev_pols) / len(prev_pols) if prev_pols else 0.0
            mean_curr_pol = sum(curr_pols) / len(curr_pols) if curr_pols else 0.0
            sentiment_drift = round(mean_curr_pol - mean_prev_pol, 4)

            # Lifecycle determination
            stage = self.classify_lifecycle_stage(
                current_volume=curr_vol,
                previous_volume=prev_vol,
                velocity=volume_velocity,
                acceleration=volume_acceleration,
            )

            # Dominant sentiment & emotion across entire topic
            sent_counts: Occurrences[str] = Occurrences()
            emo_counts: Occurrences[str] = Occurrences()
            for p in topic_posts:
                _, sent, emo = extract_post_sentiment_and_emotion(p)
                if sent:
                    sent_counts[sent] += 1
                if emo:
                    emo_counts[emo] += 1

            dom_sent = sent_counts.most_common(1)[0][0] if sent_counts else None
            dom_emo = emo_counts.most_common(1)[0][0] if emo_counts else None

            first_seen = min(topic_timestamps) if topic_timestamps else None
            last_seen = max(topic_timestamps) if topic_timestamps else None

            trajectory = NarrativeTrajectoryMetrics(
                current_volume=curr_vol,
                previous_volume=prev_vol,
                volume_velocity=volume_velocity,
                volume_acceleration=volume_acceleration,
                engagement_velocity=eng_velocity,
                sentiment_drift=sentiment_drift,
                stage=stage,
            )

            results.append(
                NarrativeIntelligence(
                    topic_id=t_id,
                    label=meta.get("label") or t_id,
                    keywords=meta.get("keywords") or [],
                    first_seen=first_seen,
                    last_seen=last_seen,
                    post_count=len(topic_posts),
                    lifecycle_stage=stage,
                    trajectory=trajectory,
                    dominant_sentiment=dom_sent,
                    dominant_emotion=dom_emo,
                    sample_post_ids=sample_ids,
                )
            )

        # Sort narratives by post count descending
        results.sort(key=lambda n: n.post_count, reverse=True)
        return results
