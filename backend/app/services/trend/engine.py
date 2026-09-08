from collections import defaultdict
from datetime import datetime, timedelta, timezone
import math
from typing import Any, Dict, List, Optional, Set, Tuple

from app.schemas.data_quality import AnalyticsReadyPost
from app.schemas.topic import ExtractedTopic
from app.schemas.trend import (
    TimeWindow,
    TopicTrendResult,
    TrendDirection,
)
from app.services.trend.base import BaseTrendEngine


def _ensure_utc(dt: datetime) -> datetime:
    """Normalizes any datetime to timezone-aware UTC datetime."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class StatisticalTrendEngine(BaseTrendEngine):
    """
    Deterministic, explainable statistical trend detection engine for social media topics.
    Evaluates temporal volume changes across configurable time windows, computing
    growth rates, statistical z-scores, velocity scores, and trajectory classifications.
    """

    def __init__(
        self,
        default_window_duration: timedelta = timedelta(hours=1),
        growth_threshold_pct: float = 25.0,
        decline_threshold_pct: float = -25.0,
        spike_z_score_threshold: float = 2.0,
        spike_growth_threshold_pct: float = 300.0,
        min_spiking_volume: int = 4,
        min_emerging_volume: int = 2,
        num_historical_windows: int = 4,
    ):
        self.default_window_duration = default_window_duration
        self.growth_threshold_pct = growth_threshold_pct
        self.decline_threshold_pct = decline_threshold_pct
        self.spike_z_score_threshold = spike_z_score_threshold
        self.spike_growth_threshold_pct = spike_growth_threshold_pct
        self.min_spiking_volume = min_spiking_volume
        self.min_emerging_volume = min_emerging_volume
        self.num_historical_windows = max(1, num_historical_windows)

    @property
    def model_name(self) -> str:
        return "insightx-trend-statistical-v1"

    def _determine_reference_time(
        self,
        posts: List[AnalyticsReadyPost],
        reference_time: Optional[datetime],
    ) -> datetime:
        """Determines the effective upper-bound evaluation timestamp."""
        if reference_time is not None:
            return _ensure_utc(reference_time)
        if posts:
            timestamps = [_ensure_utc(p.posted_at) for p in posts if p.posted_at is not None]
            if timestamps:
                return max(timestamps)
        return datetime.now(timezone.utc)

    def _build_post_lookup(
        self,
        posts: List[AnalyticsReadyPost],
    ) -> Tuple[Dict[int, AnalyticsReadyPost], Dict[str, AnalyticsReadyPost]]:
        """Builds lookup dictionaries for post resolution by ID and external ID."""
        id_map: Dict[int, AnalyticsReadyPost] = {}
        ext_map: Dict[str, AnalyticsReadyPost] = {}
        for p in posts:
            if p.id is not None:
                id_map[p.id] = p
            if p.external_post_id:
                ext_map[p.external_post_id] = p
        return id_map, ext_map

    def _get_topic_posts(
        self,
        topic: ExtractedTopic,
        posts: List[AnalyticsReadyPost],
        id_map: Dict[int, AnalyticsReadyPost],
        ext_map: Dict[str, AnalyticsReadyPost],
    ) -> List[AnalyticsReadyPost]:
        """Resolves the subset of posts associated with the specified topic cluster."""
        matched_posts: List[AnalyticsReadyPost] = []
        seen_post_obj_ids: Set[int] = set()

        for pid in topic.post_ids:
            if pid in id_map:
                post = id_map[pid]
                if id(post) not in seen_post_obj_ids:
                    seen_post_obj_ids.add(id(post))
                    matched_posts.append(post)

        for ext_id in topic.external_post_ids:
            if ext_id in ext_map:
                post = ext_map[ext_id]
                if id(post) not in seen_post_obj_ids:
                    seen_post_obj_ids.add(id(post))
                    matched_posts.append(post)

        # If no direct ID matches found, fall back to evaluating all provided posts
        if not matched_posts and posts:
            matched_posts = list(posts)

        return matched_posts


    def _calculate_growth_rate(self, current_vol: int, baseline_vol: int) -> float:
        """
        Calculates safe percentage growth rate.
        Handles zero-baseline gracefully without division-by-zero errors.
        """
        if baseline_vol > 0:
            growth = ((current_vol - baseline_vol) / float(baseline_vol)) * 100.0
            return round(growth, 2)
        else:
            if current_vol == 0:
                return 0.0
            # Zero baseline with positive volume represents emerging influx
            return round(float(current_vol * 100.0), 2)

    def _calculate_z_score(self, current_vol: int, historical_counts: List[int]) -> float:
        """Computes statistical z-score relative to historical time-window baseline."""
        if not historical_counts:
            return 0.0

        mean = sum(historical_counts) / float(len(historical_counts))
        variance = sum((x - mean) ** 2 for x in historical_counts) / float(len(historical_counts))
        std_dev = math.sqrt(variance)

        # Apply smoothing standard deviation floor to avoid division by zero in sparse counts
        effective_std = max(std_dev, 1.0)
        z = (current_vol - mean) / effective_std
        return round(z, 2)

    def analyze_topic_trend(
        self,
        topic: ExtractedTopic,
        posts: List[AnalyticsReadyPost],
        reference_time: Optional[datetime] = None,
        window_duration: Optional[timedelta] = None,
    ) -> TopicTrendResult:
        """
        Analyzes the volume trend of a single topic over current and baseline time windows.
        """
        duration = window_duration or self.default_window_duration
        ref_time = self._determine_reference_time(posts, reference_time)

        current_window = TimeWindow(start=ref_time - duration, end=ref_time)
        baseline_window = TimeWindow(start=ref_time - (2 * duration), end=ref_time - duration)

        id_map, ext_map = self._build_post_lookup(posts)
        topic_posts = self._get_topic_posts(topic, posts, id_map, ext_map)

        earliest_time = None
        for p in topic_posts:
            if p.posted_at is not None:
                pt = _ensure_utc(p.posted_at)
                if earliest_time is None or pt < earliest_time:
                    earliest_time = pt

        # Bin topic posts into time slices
        current_posts: List[AnalyticsReadyPost] = []
        baseline_posts: List[AnalyticsReadyPost] = []
        raw_hist_counts: List[int] = [0] * self.num_historical_windows

        for p in topic_posts:
            if p.posted_at is None:
                continue
            post_time = _ensure_utc(p.posted_at)

            # Check current window (start < t <= end)
            if current_window.start < post_time <= current_window.end:
                current_posts.append(p)
            # Check baseline window (start < t <= end)
            elif baseline_window.start < post_time <= baseline_window.end:
                baseline_posts.append(p)

            # Bin into historical slices for anomaly detection
            for k in range(self.num_historical_windows):
                hist_end = ref_time - ((k + 1) * duration)
                hist_start = ref_time - ((k + 2) * duration)
                if hist_start < post_time <= hist_end:
                    raw_hist_counts[k] += 1

        # First historical slice is the baseline window
        raw_hist_counts[0] = len(baseline_posts)

        # Filter to historical slices within the active data observation horizon
        active_historical: List[int] = []
        if earliest_time is not None:
            for k in range(self.num_historical_windows):
                hist_end = ref_time - ((k + 1) * duration)
                if hist_end >= earliest_time or k == 0:
                    active_historical.append(raw_hist_counts[k])
        if not active_historical:
            active_historical = [len(baseline_posts)]

        current_vol = len(current_posts)
        baseline_vol = len(baseline_posts)

        growth_rate = self._calculate_growth_rate(current_vol, baseline_vol)
        z_score = self._calculate_z_score(current_vol, active_historical)

        # Emerging narrative detection: newly appearing with 0 baseline or minimal initial seed
        is_emerging = False
        if current_vol >= self.min_emerging_volume and baseline_vol == 0:
            is_emerging = True
        elif baseline_vol == 1 and current_vol >= (self.min_emerging_volume * 2) and growth_rate >= 200.0:
            is_emerging = True

        # Spike detection: extreme surge relative to historical baseline
        is_spiking = False
        if current_vol >= self.min_spiking_volume:
            if baseline_vol >= 1 and growth_rate >= self.spike_growth_threshold_pct:
                is_spiking = True
            elif len(active_historical) > 1 and z_score >= self.spike_z_score_threshold and growth_rate >= self.growth_threshold_pct:
                is_spiking = True


        # Classify trend direction
        if is_emerging:
            direction = TrendDirection.EMERGING
        elif is_spiking:
            direction = TrendDirection.SPIKING
        elif growth_rate >= self.growth_threshold_pct:
            direction = TrendDirection.GROWING
        elif growth_rate <= self.decline_threshold_pct:
            direction = TrendDirection.DECLINING
        else:
            direction = TrendDirection.STABLE

        # Calculate composite trend velocity score
        # Higher score = stronger positive momentum / urgency
        trend_score = (
            (current_vol * 1.5)
            + (growth_rate / 25.0)
            + (5.0 if is_spiking else 0.0)
            + (3.0 if is_emerging else 0.0)
        )
        if direction == TrendDirection.DECLINING:
            trend_score = round(-1.0 * abs(growth_rate) / 20.0 + (current_vol * 0.5), 2)
        else:
            trend_score = round(max(0.0, trend_score), 2)

        # Collect post identifiers in current window
        post_ids = [p.id for p in current_posts if p.id is not None]
        ext_post_ids = [p.external_post_id for p in current_posts if p.external_post_id]

        return TopicTrendResult(
            topic_id=topic.topic_id,
            topic_label=topic.label,
            current_volume=current_vol,
            baseline_volume=baseline_vol,
            growth_rate=growth_rate,
            direction=direction,
            trend_score=trend_score,
            is_emerging=is_emerging,
            is_spiking=is_spiking,
            post_ids=post_ids,
            external_post_ids=ext_post_ids,
            current_window=current_window,
            baseline_window=baseline_window,
            details={
                "z_score": z_score,
                "historical_counts": active_historical,
                "window_duration_seconds": int(duration.total_seconds()),
                "total_topic_posts_seen": len(topic_posts),
            },

        )

    def analyze_batch_trends(
        self,
        topics: List[ExtractedTopic],
        posts: List[AnalyticsReadyPost],
        reference_time: Optional[datetime] = None,
        window_duration: Optional[timedelta] = None,
    ) -> List[TopicTrendResult]:
        """
        Analyzes temporal trends across multiple topic clusters in batch.
        Returns topic trends ordered by trend score descending.
        """
        if not topics:
            return []

        results: List[TopicTrendResult] = []
        for topic in topics:
            res = self.analyze_topic_trend(
                topic=topic,
                posts=posts,
                reference_time=reference_time,
                window_duration=window_duration,
            )
            results.append(res)

        # Sort results descending by trend_score, break ties with current_volume then topic_id
        results.sort(
            key=lambda t: (t.trend_score, t.current_volume, t.topic_id),
            reverse=True,
        )
        return results
