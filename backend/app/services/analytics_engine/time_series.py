from datetime import datetime, timedelta, timezone
from typing import Any, Counter, Dict, List, Optional, Tuple
from collections import Counter as Occurrences, defaultdict
import math

from app.schemas.analytics_engine import (
    CrossPlatformTemporalReport,
    IntervalUnit,
    PlatformTemporalSeries,
    TemporalAnomalyDetail,
    TemporalBaselineComparison,
    TemporalDynamicsReport,
    TemporalTrajectorySignal,
    TimeSeriesBucket,
)
from app.services.analytics_engine.base import BaseTimeSeriesEngine
from app.services.analytics_engine.engagement import (
    EngagementEngine,
    extract_post_metrics,
)


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
        polarity = post.get("sentiment_score") or post.get("polarity") or post.get("score")
        sentiment = post.get("sentiment")
        emotion = post.get("emotion")
    else:
        # Check direct fields
        polarity = getattr(post, "sentiment_score", None) or getattr(post, "polarity", None) or getattr(post, "score", None)
        sentiment = getattr(post, "sentiment", None)
        emotion = getattr(post, "emotion", None)

        # Check metadata dictionary
        meta = getattr(post, "metadata", None)
        if isinstance(meta, dict):
            if polarity is None:
                polarity = meta.get("sentiment_score") or meta.get("polarity") or meta.get("score")
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
    Phase 4.6 Advanced Time-Series Analytics Engine.
    Provides discrete temporal interval bucketing, moving-average smoothing,
    velocity/acceleration tracking, baseline comparisons, multi-tier anomaly detection,
    cross-platform temporal presence, deterministic trajectory signals, and temporal insights.
    """

    def __init__(
        self,
        engagement_engine: Optional[EngagementEngine] = None,
        sentiment_engine: Optional[Any] = None,
    ) -> None:
        self.engagement_engine = engagement_engine or EngagementEngine()
        if sentiment_engine is None:
            from app.services.analytics_engine.sentiment import SentimentAnalyticsEngine
            self.sentiment_engine = SentimentAnalyticsEngine()
        else:
            self.sentiment_engine = sentiment_engine

    def compare_baseline_vs_current(
        self,
        buckets: List[TimeSeriesBucket],
        split_ratio: float = 0.5,
    ) -> TemporalBaselineComparison:
        """
        Calculate historical baseline vs. current active window metrics and growth rates.
        """
        if not buckets:
            return TemporalBaselineComparison(
                baseline_period_buckets=0,
                current_period_buckets=0,
                baseline_mean_volume=0.0,
                current_mean_volume=0.0,
                volume_absolute_change=0.0,
                volume_growth_rate_pct=0.0,
                baseline_mean_engagement=0.0,
                current_mean_engagement=0.0,
                engagement_growth_rate_pct=0.0,
                baseline_mean_sentiment=None,
                current_mean_sentiment=None,
                sentiment_shift=None,
                direction="stable",
            )

        if len(buckets) == 1:
            b = buckets[0]
            return TemporalBaselineComparison(
                baseline_period_buckets=1,
                current_period_buckets=1,
                baseline_mean_volume=float(b.post_count),
                current_mean_volume=float(b.post_count),
                volume_absolute_change=0.0,
                volume_growth_rate_pct=0.0,
                baseline_mean_engagement=b.engagement_score,
                current_mean_engagement=b.engagement_score,
                engagement_growth_rate_pct=0.0,
                baseline_mean_sentiment=b.avg_sentiment_polarity,
                current_mean_sentiment=b.avg_sentiment_polarity,
                sentiment_shift=0.0 if b.avg_sentiment_polarity is not None else None,
                direction="stable",
            )

        split_idx = max(1, int(len(buckets) * split_ratio))
        base_buckets = buckets[:split_idx]
        curr_buckets = buckets[split_idx:]

        # Mean volume
        base_mean_vol = sum(b.post_count for b in base_buckets) / len(base_buckets)
        curr_mean_vol = sum(b.post_count for b in curr_buckets) / len(curr_buckets)
        vol_abs_diff = round(curr_mean_vol - base_mean_vol, 4)
        vol_growth_pct = round(
            ((curr_mean_vol - base_mean_vol) / max(abs(base_mean_vol), 1.0)) * 100.0, 2
        )

        # Mean engagement
        base_mean_eng = sum(b.engagement_score for b in base_buckets) / len(base_buckets)
        curr_mean_eng = sum(b.engagement_score for b in curr_buckets) / len(curr_buckets)
        eng_growth_pct = round(
            ((curr_mean_eng - base_mean_eng) / max(abs(base_mean_eng), 1.0)) * 100.0, 2
        )

        # Mean sentiment
        base_sent_vals = [
            b.avg_sentiment_polarity for b in base_buckets if b.avg_sentiment_polarity is not None
        ]
        curr_sent_vals = [
            b.avg_sentiment_polarity for b in curr_buckets if b.avg_sentiment_polarity is not None
        ]

        base_mean_sent = round(sum(base_sent_vals) / len(base_sent_vals), 4) if base_sent_vals else None
        curr_mean_sent = round(sum(curr_sent_vals) / len(curr_sent_vals), 4) if curr_sent_vals else None
        sent_shift = (
            round(curr_mean_sent - base_mean_sent, 4)
            if (base_mean_sent is not None and curr_mean_sent is not None)
            else None
        )

        # Direction heuristic
        if vol_growth_pct > 15.0:
            direction = "rising"
        elif vol_growth_pct < -15.0:
            direction = "declining"
        else:
            direction = "stable"

        return TemporalBaselineComparison(
            baseline_period_buckets=len(base_buckets),
            current_period_buckets=len(curr_buckets),
            baseline_mean_volume=round(base_mean_vol, 2),
            current_mean_volume=round(curr_mean_vol, 2),
            volume_absolute_change=vol_abs_diff,
            volume_growth_rate_pct=vol_growth_pct,
            baseline_mean_engagement=round(base_mean_eng, 2),
            current_mean_engagement=round(curr_mean_eng, 2),
            engagement_growth_rate_pct=eng_growth_pct,
            baseline_mean_sentiment=base_mean_sent,
            current_mean_sentiment=curr_mean_sent,
            sentiment_shift=sent_shift,
            direction=direction,
        )

    def detect_anomalies(
        self,
        buckets: List[TimeSeriesBucket],
        anomaly_threshold_z: float = 2.0,
    ) -> List[TemporalAnomalyDetail]:
        """
        Detect and classify multi-tiered temporal anomalies and spikes.
        Tiers:
        - elevated: 1.5 <= z < 2.0
        - anomalous: 2.0 <= z < 3.0
        - extreme_spike: z >= 3.0
        """
        if not buckets:
            return []

        counts = [b.post_count for b in buckets]
        mean_vol = sum(counts) / len(counts)
        var_vol = sum((x - mean_vol) ** 2 for x in counts) / len(counts) if len(counts) > 1 else 0.0
        std_vol = math.sqrt(var_vol)

        engs = [b.engagement_score for b in buckets]
        mean_eng = sum(engs) / len(engs)
        var_eng = sum((x - mean_eng) ** 2 for x in engs) / len(engs) if len(engs) > 1 else 0.0
        std_eng = math.sqrt(var_eng)

        anomalies: List[TemporalAnomalyDetail] = []

        for b in buckets:
            z_v = (b.post_count - mean_vol) / std_vol if (std_vol > 0.0 and b.post_count > 0) else 0.0
            z_e = (b.engagement_score - mean_eng) / std_eng if (std_eng > 0.0 and b.engagement_score > 0) else 0.0

            max_z = max(z_v, z_e)
            b.anomaly_score = round(max_z, 2)

            if max_z >= 1.5:
                if max_z >= 3.0:
                    severity = "extreme_spike"
                elif max_z >= 2.0:
                    severity = "anomalous"
                else:
                    severity = "elevated"

                if z_v >= z_e and z_v >= 1.5:
                    affected_metric = "volume"
                    act_val = float(b.post_count)
                    exp_val = b.rolling_post_count_avg or round(mean_vol, 2)
                    dev = round(b.post_count - exp_val, 2)
                    desc = (
                        f"Significant post volume spike of {b.post_count} posts (z-score: {z_v:.2f}, "
                        f"expected ~{exp_val:.1f})."
                    )
                elif z_e > z_v and z_e >= 1.5:
                    affected_metric = "engagement"
                    act_val = b.engagement_score
                    exp_val = b.rolling_engagement_avg or round(mean_eng, 2)
                    dev = round(b.engagement_score - exp_val, 2)
                    desc = (
                        f"Significant engagement spike of {b.engagement_score:,.1f} score (z-score: {z_e:.2f}, "
                        f"expected ~{exp_val:,.1f})."
                    )
                else:
                    affected_metric = "combined"
                    act_val = float(b.post_count)
                    exp_val = round(mean_vol, 2)
                    dev = round(b.post_count - exp_val, 2)
                    desc = f"Elevated volume and engagement activity (z-score: {max_z:.2f})."

                b.anomaly_severity = severity
                b.anomaly_metric = affected_metric
                b.is_anomaly = (max_z >= anomaly_threshold_z)

                anomalies.append(
                    TemporalAnomalyDetail(
                        bucket_start=b.bucket_start,
                        bucket_end=b.bucket_end,
                        z_score=round(max_z, 2),
                        moving_avg_deviation=dev,
                        severity=severity,
                        affected_metric=affected_metric,
                        actual_value=act_val,
                        expected_baseline=exp_val,
                        description=desc,
                    )
                )
            else:
                b.anomaly_severity = "normal"
                b.anomaly_metric = None
                b.is_anomaly = False

        return anomalies

    def evaluate_trajectory(
        self,
        buckets: List[TimeSeriesBucket],
    ) -> TemporalTrajectorySignal:
        """
        Evaluate deterministic short-term trajectory signals based on trailing intervals.
        (Heuristic velocity/acceleration classification, not predictive ML).
        """
        if not buckets or len(buckets) < 2:
            return TemporalTrajectorySignal(
                classification="insufficient_data",
                recent_velocity=0.0,
                recent_acceleration=0.0,
                confidence_score=0.2 if buckets else 0.0,
                explanation="Insufficient interval observations to establish a trajectory trend.",
            )

        # Inspect trailing intervals (up to last 3)
        trailing = buckets[-3:]
        velocities = [
            b.velocity for b in trailing if b.velocity is not None
        ]
        accelerations = [
            b.acceleration for b in trailing if b.acceleration is not None
        ]

        recent_v = velocities[-1] if velocities else 0.0
        recent_a = accelerations[-1] if accelerations else 0.0

        conf = min(1.0, len(buckets) / 5.0)

        if recent_v >= 3.0 and recent_a > 0.0:
            classification = "rapidly_rising"
            explanation = f"Signal is accelerating rapidly with positive volume velocity (+{recent_v:.1f}) and acceleration (+{recent_a:.1f})."
        elif recent_v > 0.0:
            classification = "rising"
            explanation = f"Signal is trending upward with recent positive volume velocity (+{recent_v:.1f})."
        elif recent_v <= -3.0 and recent_a < 0.0:
            classification = "rapidly_declining"
            explanation = f"Signal is decelerating rapidly with steep negative velocity ({recent_v:.1f})."
        elif recent_v < 0.0:
            classification = "declining"
            explanation = f"Signal is tapering downward with recent negative velocity ({recent_v:.1f})."
        else:
            classification = "stable"
            explanation = "Signal exhibits stable volume velocity across recent observation intervals."

        return TemporalTrajectorySignal(
            classification=classification,
            recent_velocity=round(recent_v, 2),
            recent_acceleration=round(recent_a, 2),
            confidence_score=round(conf, 2),
            explanation=explanation,
        )

    def compare_platforms_temporal(
        self,
        posts: List[Any],
        interval_unit: IntervalUnit = IntervalUnit.HOUR,
    ) -> CrossPlatformTemporalReport:
        """
        Compare temporal timeline dynamics across publishing platforms.
        """
        if not posts:
            return CrossPlatformTemporalReport(platforms={})

        platform_posts_map: Dict[str, List[Any]] = defaultdict(list)
        for post in posts:
            _, _, _, _, platform = extract_post_metrics(post)
            platform_posts_map[platform].append(post)

        total_posts_all = len(posts)
        platform_series: Dict[str, PlatformTemporalSeries] = {}

        for plat_name, plat_posts in sorted(platform_posts_map.items()):
            plat_ts = [
                extract_post_timestamp(p) for p in plat_posts
                if extract_post_timestamp(p) is not None
            ]
            earliest_ts = min(plat_ts) if plat_ts else None

            # Group posts into interval buckets for this platform
            plat_bucket_counts: Dict[datetime, int] = defaultdict(int)
            plat_bucket_eng: Dict[datetime, float] = defaultdict(float)

            for p in plat_posts:
                ts = extract_post_timestamp(p)
                if ts:
                    b_fl = floor_to_interval(ts, interval_unit)
                    plat_bucket_counts[b_fl] += 1
                    l, c, s, _, _ = extract_post_metrics(p)
                    plat_bucket_eng[b_fl] += self.engagement_engine.calculate_post_weighted_score(l, c, s)

            total_plat_eng = self.engagement_engine.calculate_engagement(plat_posts).weighted_engagement_score

            peak_b_start = None
            peak_vol = 0
            peak_eng = 0.0

            for b_time, count in plat_bucket_counts.items():
                if count > peak_vol or (count == peak_vol and plat_bucket_eng[b_time] > peak_eng):
                    peak_vol = count
                    peak_eng = plat_bucket_eng[b_time]
                    peak_b_start = b_time

            # Compute growth rate across platform intervals
            sorted_bucket_times = sorted(plat_bucket_counts.keys())
            if len(sorted_bucket_times) >= 2:
                split = len(sorted_bucket_times) // 2
                base_cnt = sum(plat_bucket_counts[t] for t in sorted_bucket_times[:split]) / max(split, 1)
                curr_cnt = sum(plat_bucket_counts[t] for t in sorted_bucket_times[split:]) / max(len(sorted_bucket_times) - split, 1)
                growth_rate = round(((curr_cnt - base_cnt) / max(base_cnt, 1.0)) * 100.0, 2)
            else:
                growth_rate = 0.0

            share_pct = round((len(plat_posts) / max(total_posts_all, 1)) * 100.0, 2)

            platform_series[plat_name] = PlatformTemporalSeries(
                platform=plat_name,
                total_posts=len(plat_posts),
                total_engagement=round(total_plat_eng, 2),
                earliest_activity=earliest_ts,
                peak_bucket_start=peak_b_start,
                peak_volume=peak_vol,
                peak_engagement=round(peak_eng, 2),
                growth_rate_pct=growth_rate,
                volume_share_pct=share_pct,
            )

        # Leaders
        valid_platforms = [p for p in platform_series.values() if p.total_posts > 0]
        earliest_plat = min(
            (p for p in valid_platforms if p.earliest_activity is not None),
            key=lambda p: p.earliest_activity,
            default=None,
        )
        peak_vol_plat = max(valid_platforms, key=lambda p: p.peak_volume, default=None)
        peak_eng_plat = max(valid_platforms, key=lambda p: p.peak_engagement, default=None)
        highest_growth_plat = max(valid_platforms, key=lambda p: p.growth_rate_pct, default=None)

        return CrossPlatformTemporalReport(
            platforms=platform_series,
            earliest_platform=earliest_plat.platform if earliest_plat else None,
            peak_volume_platform=peak_vol_plat.platform if peak_vol_plat else None,
            peak_engagement_platform=peak_eng_plat.platform if peak_eng_plat else None,
            highest_growth_platform=highest_growth_plat.platform if highest_growth_plat else None,
        )

    def _generate_temporal_insights(
        self,
        report: TemporalDynamicsReport,
    ) -> List[str]:
        """Generate human-readable, deterministic temporal insight statements."""
        insights: List[str] = []

        if report.total_buckets == 0:
            insights.append("No temporal data available for interval analysis.")
            return insights

        # 1. Baseline vs Current comparison insight
        if report.baseline_comparison and report.total_buckets >= 2:
            bc = report.baseline_comparison
            if bc.volume_growth_rate_pct > 15.0:
                insights.append(
                    f"Post volume increased {bc.volume_growth_rate_pct:+.1f}% compared with the historical baseline."
                )
            elif bc.volume_growth_rate_pct < -15.0:
                insights.append(
                    f"Post volume declined {abs(bc.volume_growth_rate_pct):.1f}% compared with the historical baseline."
                )

            if bc.engagement_growth_rate_pct > 20.0:
                insights.append(
                    f"Engagement grew {bc.engagement_growth_rate_pct:+.1f}% across recent observation periods."
                )

            if bc.sentiment_shift is not None and abs(bc.sentiment_shift) >= 0.2:
                shift_dir = "improved" if bc.sentiment_shift > 0 else "declined"
                insights.append(
                    f"Average sentiment {shift_dir} by {abs(bc.sentiment_shift):.2f} polarity points between baseline and current periods."
                )

        # 2. Peak activity insight
        if report.peak_bucket_start is not None and report.peak_bucket_volume > 0:
            peak_fmt = report.peak_bucket_start.strftime("%Y-%m-%d %H:%M UTC")
            insights.append(
                f"Peak interval occurred at {peak_fmt} with {report.peak_bucket_volume} posts "
                f"generating {report.peak_bucket_engagement:,.1f} weighted engagement."
            )

        # 3. Anomaly and spike insights
        if report.detected_anomalies:
            extreme_spikes = [a for a in report.detected_anomalies if a.severity == "extreme_spike"]
            if extreme_spikes:
                top_spike = extreme_spikes[0]
                insights.append(
                    f"Extreme temporal spike detected at {top_spike.bucket_start.strftime('%Y-%m-%d %H:%M UTC')} "
                    f"({top_spike.description})."
                )
            elif report.anomalous_intervals_count > 0:
                insights.append(
                    f"Detected {report.anomalous_intervals_count} statistically significant temporal activity spike(s)."
                )

        # 4. Trajectory insight
        if report.trajectory_signal and report.trajectory_signal.classification != "insufficient_data":
            traj = report.trajectory_signal
            insights.append(
                f"Near-term temporal trajectory is {traj.classification.replace('_', ' ').upper()} ({traj.explanation})."
            )

        # 5. Cross-platform timing insight
        if report.platform_temporal_comparison and len(report.platform_temporal_comparison.platforms) > 1:
            cp = report.platform_temporal_comparison
            if cp.earliest_platform and cp.peak_volume_platform and cp.earliest_platform != cp.peak_volume_platform:
                insights.append(
                    f"Activity initiated earliest on '{cp.earliest_platform}' while highest peak volume concentrated on '{cp.peak_volume_platform}'."
                )

        return insights

    def generate_time_series(
        self,
        posts: List[Any],
        interval_unit: IntervalUnit = IntervalUnit.HOUR,
        rolling_window_size: int = 3,
        anomaly_threshold_z: float = 2.0,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        split_ratio: float = 0.5,
    ) -> TemporalDynamicsReport:
        """
        Generate discrete temporal buckets with rolling statistics, peak/anomaly detection,
        baseline comparison, cross-platform analysis, trajectory modeling, and insights.
        """
        if not posts:
            now_utc = datetime.now(timezone.utc)
            empty_report = TemporalDynamicsReport(
                interval_unit=interval_unit,
                total_buckets=0,
                start_time=start_time or now_utc,
                end_time=end_time or now_utc,
                buckets=[],
                peak_bucket_start=None,
                peak_bucket_volume=0,
                peak_bucket_engagement=0.0,
                anomalous_intervals_count=0,
                baseline_comparison=None,
                detected_anomalies=[],
                platform_temporal_comparison=None,
                trajectory_signal=None,
                temporal_insights=["No posts provided for temporal analysis."],
            )
            return empty_report

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
                baseline_comparison=None,
                detected_anomalies=[],
                platform_temporal_comparison=None,
                trajectory_signal=None,
                temporal_insights=["No valid timestamps found for temporal analysis."],
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
            platform_counts: Dict[str, int] = defaultdict(int)

            for p in b_posts:
                l, c, s, v, plat = extract_post_metrics(p)
                likes += l
                comments += c
                shares += s
                views += v
                platform_counts[plat] += 1

                pol, sent, emo = extract_post_sentiment_and_emotion(p)
                if pol is None or sent is None:
                    s_prof = self.sentiment_engine.analyze_post(p)
                    if pol is None:
                        pol = s_prof.score
                    if sent is None:
                        sent = s_prof.label.lower()

                if pol is not None:
                    polarities.append(pol)
                if sent:
                    sentiment_counts[sent] += 1
                if emo:
                    emotion_counts[emo] += 1

            eng_score = self.engagement_engine.calculate_post_weighted_score(likes, comments, shares)
            avg_post_eng = round(eng_score / max(len(b_posts), 1), 2) if b_posts else 0.0
            avg_pol = round(sum(polarities) / len(polarities), 4) if polarities else None
            dom_sent = sentiment_counts.most_common(1)[0][0] if sentiment_counts else None
            dom_emo = emotion_counts.most_common(1)[0][0] if emotion_counts else None

            # Sentiment percentages in bucket
            b_total = max(len(b_posts), 1)
            pos_c = sentiment_counts.get("positive", 0)
            neg_c = sentiment_counts.get("negative", 0)
            neu_c = sentiment_counts.get("neutral", 0)

            pos_pct = round((pos_c / b_total) * 100.0, 2) if b_posts else 0.0
            neg_pct = round((neg_c / b_total) * 100.0, 2) if b_posts else 0.0
            neu_pct = round((neu_c / b_total) * 100.0, 2) if b_posts else 0.0
            net_sent = round((pos_c - neg_c) / b_total, 4) if b_posts else None

            buckets.append(
                TimeSeriesBucket(
                    bucket_start=b_start,
                    bucket_end=b_end,
                    post_count=len(b_posts),
                    engagement_score=eng_score,
                    avg_post_engagement=avg_post_eng,
                    total_likes=likes,
                    total_comments=comments,
                    total_shares=shares,
                    total_views=views,
                    avg_sentiment_polarity=avg_pol,
                    net_sentiment_score=net_sent,
                    positive_percentage=pos_pct,
                    negative_percentage=neg_pct,
                    neutral_percentage=neu_pct,
                    dominant_sentiment=dom_sent,
                    dominant_emotion=dom_emo,
                    rolling_post_count_avg=None,
                    rolling_engagement_avg=None,
                    rolling_sentiment_avg=None,
                    velocity=None,
                    acceleration=None,
                    engagement_velocity=None,
                    is_anomaly=False,
                    anomaly_score=0.0,
                    anomaly_severity="normal",
                    anomaly_metric=None,
                    platform_distribution=dict(platform_counts),
                )
            )

        # Compute moving averages (smoothing)
        k = max(1, rolling_window_size)
        for i, b in enumerate(buckets):
            window_start_idx = max(0, i - k + 1)
            window_slice = buckets[window_start_idx : i + 1]
            avg_count = sum(item.post_count for item in window_slice) / len(window_slice)
            avg_eng = sum(item.engagement_score for item in window_slice) / len(window_slice)
            sent_slice = [item.avg_sentiment_polarity for item in window_slice if item.avg_sentiment_polarity is not None]
            avg_sent = round(sum(sent_slice) / len(sent_slice), 4) if sent_slice else None

            b.rolling_post_count_avg = round(avg_count, 2)
            b.rolling_engagement_avg = round(avg_eng, 2)
            b.rolling_sentiment_avg = avg_sent

        # Compute velocity and acceleration
        for i, b in enumerate(buckets):
            if i > 0:
                prev_b = buckets[i - 1]
                v = float(b.post_count - prev_b.post_count)
                e_v = float(b.engagement_score - prev_b.engagement_score)
                b.velocity = round(v, 4)
                b.engagement_velocity = round(e_v, 4)

                if i > 1:
                    prev_v = buckets[i - 1].velocity or 0.0
                    b.acceleration = round(v - prev_v, 4)
                else:
                    b.acceleration = round(v, 4)
            else:
                b.velocity = 0.0
                b.acceleration = 0.0
                b.engagement_velocity = 0.0

        # Anomaly and spike detection
        detected_anomalies = self.detect_anomalies(buckets, anomaly_threshold_z=anomaly_threshold_z)
        anomalous_count = sum(1 for b in buckets if b.is_anomaly)

        # Peak tracking
        peak_volume = 0
        peak_engagement = 0.0
        peak_start = None
        for b in buckets:
            if b.post_count > peak_volume or (b.post_count == peak_volume and b.engagement_score > peak_engagement):
                peak_volume = b.post_count
                peak_engagement = b.engagement_score
                peak_start = b.bucket_start

        # Baseline vs current comparison
        baseline_comp = self.compare_baseline_vs_current(buckets, split_ratio=split_ratio)

        # Cross-platform temporal analysis
        platform_comp = self.compare_platforms_temporal(posts, interval_unit=interval_unit)

        # Trajectory signal evaluation
        trajectory_signal = self.evaluate_trajectory(buckets)

        partial_report = TemporalDynamicsReport(
            interval_unit=interval_unit,
            total_buckets=len(buckets),
            start_time=bucket_boundaries[0] if bucket_boundaries else None,
            end_time=bucket_boundaries[-1] + step if bucket_boundaries else None,
            buckets=buckets,
            peak_bucket_start=peak_start,
            peak_bucket_volume=peak_volume,
            peak_bucket_engagement=peak_engagement,
            anomalous_intervals_count=anomalous_count,
            baseline_comparison=baseline_comp,
            detected_anomalies=detected_anomalies,
            platform_temporal_comparison=platform_comp,
            trajectory_signal=trajectory_signal,
            temporal_insights=[],
        )

        insights = self._generate_temporal_insights(partial_report)
        partial_report.temporal_insights = insights

        return partial_report
