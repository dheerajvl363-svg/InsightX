from datetime import datetime, timedelta, timezone
from typing import Any, Counter, Dict, List, Optional, Tuple
import math
from collections import Counter as Occurrences

from app.schemas.analytics_engine import (
    IntervalUnit,
    TemporalDynamicsReport,
    TimeSeriesBucket,
)
from app.services.analytics_engine.base import BaseTimeSeriesEngine
from app.services.analytics_engine.engagement import EngagementEngine, extract_post_metrics


def parse_timestamp_to_utc(val: Any) -> Optional[datetime]:
    """Parse various timestamp representations into a UTC datetime."""
    if val is None:
        return None
    if isinstance(val, datetime):
        if val.tzinfo is None:
            return val.replace(tzinfo=timezone.utc)
        return val.astimezone(timezone.utc)
    if isinstance(val, (int, float)):
        try:
            return datetime.fromtimestamp(val, tz=timezone.utc)
        except Exception:
            return None
    if isinstance(val, str):
        try:
            # Handle standard ISO string
            dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            return None
    return None


def extract_post_timestamp(post: Any) -> Optional[datetime]:
    """Extract creation timestamp from any supported post model."""
    if isinstance(post, dict):
        raw_ts = post.get("posted_at") or post.get("created_at")
    else:
        raw_ts = getattr(post, "posted_at", None) or getattr(post, "created_at", None)
    return parse_timestamp_to_utc(raw_ts)


def extract_post_sentiment_and_emotion(post: Any) -> Tuple[Optional[float], Optional[str], Optional[str]]:
    """Extract sentiment polarity, dominant sentiment, and dominant emotion if present."""
    polarity = None
    sentiment = None
    emotion = None

    if isinstance(post, dict):
        polarity = post.get("sentiment_score") or post.get("polarity")
        sentiment = post.get("sentiment")
        emotion = post.get("emotion")
    else:
        # Check direct fields
        polarity = getattr(post, "sentiment_score", None) or getattr(post, "polarity", None)
        sentiment = getattr(post, "sentiment", None)
        emotion = getattr(post, "emotion", None)

        # Check metadata dictionary
        meta = getattr(post, "metadata", None)
        if isinstance(meta, dict):
            if polarity is None:
                polarity = meta.get("sentiment_score") or meta.get("polarity")
            if sentiment is None:
                sentiment = meta.get("sentiment")
            if emotion is None:
                emotion = meta.get("emotion")

    if polarity is not None:
        try:
            polarity = float(polarity)
        except (ValueError, TypeError):
            polarity = None

    if sentiment is not None:
        sentiment = str(sentiment).lower()

    if emotion is not None:
        emotion = str(emotion).lower()

    return polarity, sentiment, emotion


def floor_to_interval(dt: datetime, interval_unit: IntervalUnit) -> datetime:
    """Floor a UTC datetime to the start of its interval window."""
    if interval_unit == IntervalUnit.HOUR:
        return datetime(dt.year, dt.month, dt.day, dt.hour, 0, 0, tzinfo=timezone.utc)
    elif interval_unit == IntervalUnit.DAY:
        return datetime(dt.year, dt.month, dt.day, 0, 0, 0, tzinfo=timezone.utc)
    elif interval_unit == IntervalUnit.WEEK:
        # Floor to Monday 00:00:00
        start_of_day = datetime(dt.year, dt.month, dt.day, 0, 0, 0, tzinfo=timezone.utc)
        return start_of_day - timedelta(days=dt.weekday())
    return dt


def interval_timedelta(interval_unit: IntervalUnit) -> timedelta:
    """Get the timedelta corresponding to one discrete interval bucket."""
    if interval_unit == IntervalUnit.HOUR:
        return timedelta(hours=1)
    elif interval_unit == IntervalUnit.DAY:
        return timedelta(days=1)
    elif interval_unit == IntervalUnit.WEEK:
        return timedelta(weeks=1)
    return timedelta(hours=1)


class TimeSeriesDynamicsEngine(BaseTimeSeriesEngine):
    """
    Time-series dynamics engine for generating discrete temporal intervals,
    calculating moving averages, tracking sentiment evolution, and identifying anomalous volume spikes.
    """

    def __init__(self, engagement_engine: Optional[EngagementEngine] = None) -> None:
        self.engagement_engine = engagement_engine or EngagementEngine()

    def generate_time_series(
        self,
        posts: List[Any],
        interval_unit: IntervalUnit = IntervalUnit.HOUR,
        rolling_window_size: int = 3,
        anomaly_threshold_z: float = 2.0,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> TemporalDynamicsReport:
        """Generate discrete temporal buckets with rolling averages and anomaly flags."""
        if not posts:
            now_utc = datetime.now(timezone.utc)
            return TemporalDynamicsReport(
                interval_unit=interval_unit,
                total_buckets=0,
                start_time=start_time or now_utc,
                end_time=end_time or now_utc,
                buckets=[],
                peak_bucket_start=None,
                peak_bucket_volume=0,
                peak_bucket_engagement=0.0,
                anomalous_intervals_count=0,
            )

        # Collect post timestamps and associated metrics
        valid_items: List[Tuple[datetime, Any]] = []
        for post in posts:
            ts = extract_post_timestamp(post)
            if ts is not None:
                valid_items.append((ts, post))

        if not valid_items:
            now_utc = datetime.now(timezone.utc)
            return TemporalDynamicsReport(
                interval_unit=interval_unit,
                total_buckets=0,
                start_time=start_time or now_utc,
                end_time=end_time or now_utc,
                buckets=[],
                peak_bucket_start=None,
                peak_bucket_volume=0,
                peak_bucket_engagement=0.0,
                anomalous_intervals_count=0,
            )

        # Determine start and end window
        timestamps = [item[0] for item in valid_items]
        min_ts = min(timestamps)
        max_ts = max(timestamps)

        report_start = floor_to_interval(start_time if start_time else min_ts, interval_unit)
        report_end_anchor = end_time if end_time else max_ts
        report_end_floor = floor_to_interval(report_end_anchor, interval_unit)
        step = interval_timedelta(interval_unit)

        # Generate sequence of bucket start boundaries
        bucket_boundaries: List[datetime] = []
        curr = report_start
        # Ensure we cover up to and including the latest bucket
        while curr <= report_end_floor:
            bucket_boundaries.append(curr)
            curr += step

        if not bucket_boundaries:
            bucket_boundaries = [report_start]

        # Group posts into buckets
        bucket_posts_map: Dict[datetime, List[Any]] = {b: [] for b in bucket_boundaries}
        for ts, post in valid_items:
            b_start = floor_to_interval(ts, interval_unit)
            if b_start in bucket_posts_map:
                bucket_posts_map[b_start].append(post)
            elif b_start < bucket_boundaries[0]:
                bucket_posts_map[bucket_boundaries[0]].append(post)
            elif b_start > bucket_boundaries[-1]:
                bucket_posts_map[bucket_boundaries[-1]].append(post)

        # Build basic bucket models
        buckets: List[TimeSeriesBucket] = []
        for b_start in bucket_boundaries:
            b_end = b_start + step
            b_posts = bucket_posts_map[b_start]

            likes = 0
            comments = 0
            shares = 0
            views = 0
            polarities: List[float] = []
            sentiment_counts: Occurrences[str] = Occurrences()
            emotion_counts: Occurrences[str] = Occurrences()

            for p in b_posts:
                l, c, s, v, _ = extract_post_metrics(p)
                likes += l
                comments += c
                shares += s
                views += v

                pol, sent, emo = extract_post_sentiment_and_emotion(p)
                if pol is not None:
                    polarities.append(pol)
                if sent:
                    sentiment_counts[sent] += 1
                if emo:
                    emotion_counts[emo] += 1

            eng_score = self.engagement_engine.calculate_post_weighted_score(likes, comments, shares)
            avg_pol = round(sum(polarities) / len(polarities), 4) if polarities else None
            dom_sent = sentiment_counts.most_common(1)[0][0] if sentiment_counts else None
            dom_emo = emotion_counts.most_common(1)[0][0] if emotion_counts else None

            buckets.append(
                TimeSeriesBucket(
                    bucket_start=b_start,
                    bucket_end=b_end,
                    post_count=len(b_posts),
                    engagement_score=eng_score,
                    total_likes=likes,
                    total_comments=comments,
                    total_shares=shares,
                    total_views=views,
                    avg_sentiment_polarity=avg_pol,
                    dominant_sentiment=dom_sent,
                    dominant_emotion=dom_emo,
                    rolling_post_count_avg=None,
                    rolling_engagement_avg=None,
                    is_anomaly=False,
                    anomaly_score=0.0,
                )
            )

        # Compute rolling averages
        k = max(1, rolling_window_size)
        for i, b in enumerate(buckets):
            window_start_idx = max(0, i - k + 1)
            window_slice = buckets[window_start_idx : i + 1]
            avg_count = sum(item.post_count for item in window_slice) / len(window_slice)
            avg_eng = sum(item.engagement_score for item in window_slice) / len(window_slice)
            b.rolling_post_count_avg = round(avg_count, 2)
            b.rolling_engagement_avg = round(avg_eng, 2)

        # Calculate volume anomaly z-scores across all buckets
        counts = [b.post_count for b in buckets]
        mean_count = sum(counts) / len(counts) if counts else 0.0
        variance = sum((x - mean_count) ** 2 for x in counts) / len(counts) if len(counts) > 1 else 0.0
        std_dev = math.sqrt(variance)

        anomalous_count = 0
        peak_volume = 0
        peak_engagement = 0.0
        peak_start = None

        for b in buckets:
            # Anomaly check
            if std_dev > 0.0 and b.post_count > 0:
                z = (b.post_count - mean_count) / std_dev
                b.anomaly_score = round(z, 2)
                if z >= anomaly_threshold_z:
                    b.is_anomaly = True
                    anomalous_count += 1
            else:
                b.anomaly_score = 0.0
                b.is_anomaly = False

            # Peak tracking
            if b.post_count > peak_volume or (b.post_count == peak_volume and b.engagement_score > peak_engagement):
                peak_volume = b.post_count
                peak_engagement = b.engagement_score
                peak_start = b.bucket_start

        return TemporalDynamicsReport(
            interval_unit=interval_unit,
            total_buckets=len(buckets),
            start_time=bucket_boundaries[0] if bucket_boundaries else None,
            end_time=bucket_boundaries[-1] + step if bucket_boundaries else None,
            buckets=buckets,
            peak_bucket_start=peak_start,
            peak_bucket_volume=peak_volume,
            peak_bucket_engagement=peak_engagement,
            anomalous_intervals_count=anomalous_count,
        )
