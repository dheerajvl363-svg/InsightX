# InsightX — Phase 4: Advanced Analytics Engine

## 1. Phase Overview & SIH PS 26152 Objective

Phase 4 establishes the high-level **Analytics Engine** for **InsightX**, synthesizing raw ingestion (Phase 2) and NLP signals (Phase 3) into holistic, multi-dimensional public intelligence for **Smart India Hackathon 2026 Problem Statement 26152 (Social Media Analytics)**.

While Phase 3 provides atomic NLP inferences (sentiment, emotion, topic clusters, demographics), Phase 4 introduces **dynamic synthesis across time, engagement depth, virality mechanics, sentiment distributions, trend momentum, temporal acceleration, and evolving narrative lifecycles**.

---

## 2. Analytics Engine Architecture (Phase 4.1 – 4.6)

The Analytics Engine is structured into decoupled, modular components orchestrated by `AnalyticsEngineService`:

```text
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       Phase 4 Analytics Engine                                         │
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                                    │
       ┌────────────────────────────┬───────────────┼───────────────┬────────────────────────────┐
       ↓                            ↓               ↓               ↓                            ↓
┌──────────────┐             ┌──────────────┐┌──────────────┐┌──────────────┐             ┌──────────────┐
│  Engagement  │             │ Time-Series  ││  Sentiment   ││    Trend     │             │  Narrative   │
│    Engine    │             │   Dynamics   ││    Engine    ││  Detection   │             │   Dynamics   │
│ (Phase 4.2)  │             │ (Phase 4.6)  ││ (Phase 4.3)  ││ (Phase 4.4)  │             │ (Phase 4.5)  │
└──────────────┘             └──────────────┘└──────────────┘└──────────────┘             └──────────────┘
       │                            │               │               │                            │
       │ • Weighted score           │ • Bucketing   │ • Polarity    │ • Mining/Spikes            │ • Lifecycle stages
       │ • Virality & Amplification │ • Smoothing   │ • Net score   │ • Momentum score           │ • Velocity & accel.
       │ • Discussion depth         │ • Velocity    │ • Dist %      │ • Direction classification │ • Sentiment drift
       │ • Score distribution       │ • Anomaly z   │ • Platform    │ • Platform summaries       │ • Impact score
       │ • Platform benchmarking    │ • Trajectory  └───────┬───────┴────────────┬───────────────┤ • Multi-platform
       └────────────────────────────┼───────────────────────┤                    │               └──────┬───────┘
                                    │                       ↓                    ↓                      │
                                    │    ┌──────────────────────────────────────────────┐               │
                                    └───►│            AnalyticsEngineService            │◄──────────────┘
                                         │       (Orchestrator & Insights Engine)       │
                                         └──────────────────────┬───────────────────────┘
                                                                ↓
                                         ┌──────────────────────────────────────────────┐
                                         │            Phase4AnalyticsReport             │
                                         │       (Unified Multi-Signal Output)          │
                                         └──────────────────────────────────────────────┘
```

---

## 3. Mathematical Foundations & Metrics

### 3.1 Engagement & Virality Formulation (Phase 4.2)

- **Weighted Engagement Score ($E$)**:
  $$E = (likes \times 1.0) + (comments \times 2.0) + (shares \times 3.0)$$
- **Virality Index ($V$)**:
  $$V = \frac{total\_shares}{\max(total\_likes, 1)}$$
- **Amplification Rate ($AR$)**:
  $$AR = \frac{total\_shares}{\max(total\_interactions, 1)} \quad \text{where } total\_interactions = likes + comments + shares$$
- **Discussion Depth ($D$)**:
  $$D = \frac{total\_comments}{\max(total\_likes, 1)}$$
- **Conversation Rate ($CR$)**:
  $$CR = \frac{total\_comments}{\max(total\_interactions, 1)}$$
- **Engagement Rate per Impression ($ER$)**:
  $$ER = \frac{total\_likes + total\_comments + total\_shares}{\max(total\_views, 1)} \quad (\text{when } total\_views > 0)$$
- **Average Post Engagement ($\overline{E}$)**:
  $$\overline{E} = \frac{E}{total\_posts}$$
- **Statistical Distribution of Engagement Scores**:
  - Minimum, Maximum, Mean ($\mu$), Median, Standard Deviation ($\sigma$), $25^{\text{th}}$ percentile ($Q_1$), $75^{\text{th}}$ percentile ($Q_3$).
- **Outlier Post Detection**:
  $$\text{Threshold}_{outlier} = \mu_{E} + (k \cdot \sigma_{E}) \quad (\text{default } k = 2.0\sigma)$$
- **Cross-Platform Benchmarking**:
  - $\text{Post Share \%} = \frac{N_{platform}}{N_{total}} \times 100$
  - $\text{Engagement Share \%} = \frac{E_{platform}}{E_{total}} \times 100$
  - Efficiency Ranking: Ordered rank by $\overline{E}_{platform}$ descending (Rank 1 = most engaging platform).

---

### 3.2 Sentiment Analytics Formulation (Phase 4.3)

- **Per-Post Polarity Score ($s_i$)**:
  $$s_i \in [-1.0, 1.0]$$
  Calculated via valence lexicon dictionary, emoji parsing, negation modifiers, and capitalization intensifiers.
- **Sentiment Classification ($label_i$)**:
  $$label_i = \begin{cases} \text{positive} & \text{if } s_i > +0.05 \\ \text{negative} & \text{if } s_i < -0.05 \\ \text{neutral} & \text{otherwise} \end{cases}$$
- **Sentiment Percentages**:
  $$\text{Positive \%} = \frac{N_{pos}}{N_{total}} \times 100, \quad \text{Neutral \%} = \frac{N_{neu}}{N_{total}} \times 100, \quad \text{Negative \%} = \frac{N_{neg}}{N_{total}} \times 100$$
- **Net Sentiment Score ($\text{NSS}$)**:
  $$\text{NSS} = \frac{N_{pos} - N_{neg}}{\max(N_{total}, 1)} \in [-1.0, 1.0]$$
- **Platform Sentiment Partitioning**:
  $$\text{NSS}_{platform} = \frac{N_{pos, p} - N_{neg, p}}{\max(N_{total, p}, 1)}$$
- **Temporal Sentiment Trajectory**:
  $$\text{NSS}_{bucket}(t) = \frac{N_{pos}(t) - N_{neg}(t)}{\max(N(t), 1)}, \quad \overline{s}(t) = \frac{1}{N(t)} \sum_{j \in bucket(t)} s_j$$

---

### 3.3 Trend Detection & Momentum Formulation (Phase 4.4)

Trend detection isolates entities (topics, hashtags, extracted keywords) gaining or losing velocity, distinguishing **true dynamic momentum** from high static volume.

- **Velocity ($v$)**:
  $$v = \text{volume}_{current} - \text{volume}_{baseline}$$
- **Acceleration ($a$)**:
  $$a = v - \text{volume}_{baseline} \quad (\text{when } \text{volume}_{baseline} > 0)$$
- **Growth Rate Percentage ($\text{GR}_{\%}$)**:
  $$\text{GR}_{\%} = \begin{cases} \frac{\text{volume}_{current} - \text{volume}_{baseline}}{\text{volume}_{baseline}} \times 100 & \text{if } \text{volume}_{baseline} > 0 \\ \text{volume}_{current} \times 100 & \text{otherwise} \end{cases}$$
- **Engagement Amplification Factor ($F_{eng}$)**:
  $$F_{eng} = 1.0 + \min\left(2.0, \frac{\overline{E}_{topic}}{100.0}\right)$$
- **Growth Multiplier ($M_{growth}$)**:
  $$M_{growth} = \log_2\left(2.0 + \frac{\max(0, \text{GR}_{\%})}{100.0}\right)$$
- **Momentum Score ($S_{momentum}$)**:
  $$S_{momentum} = \begin{cases} \text{volume}_{current} \times 2.5 \times M_{growth} \times F_{eng} & \text{if spiking} \\ \text{volume}_{current} \times 2.0 \times F_{eng} & \text{if emerging} \\ v \times M_{growth} \times F_{eng} & \text{if accelerating} \\ v \times \left(\frac{1}{\max(1.0, F_{eng})}\right) & \text{if declining} \\ \max(0.1, \text{volume}_{current} \times 0.1) & \text{if stable} \end{cases}$$
- **Trend Classifications**:
  - `emerging`: Topic has 0 baseline volume and > 0 current volume.
  - `spiking`: Topic has $z$-score $\ge 2.0$ or ($\text{GR}_{\%} \ge 200\%$ with $\text{volume}_{current} \ge 3$).
  - `accelerating`: Velocity $> 0$ and acceleration $> 0$.
  - `declining`: Velocity $< 0$.
  - `stable`: Velocity $\approx 0$.

---

### 3.4 Narrative Analysis & Impact Scoring (Phase 4.5)

Narratives represent cohesive conversational themes evolving across time and platforms.

- **Narrative Lifecycle State Machine**:
  Topics and discussion threads progress across deterministic lifecycle stages based on temporal volume velocity ($v = \text{vol}_{curr} - \text{vol}_{prev}$) and acceleration ($a = v - \text{vol}_{prev}$):

  | Lifecycle Stage | Condition | Description |
  | :--- | :--- | :--- |
  | `EMERGING` | $\text{vol}_{prev} = 0 \land \text{vol}_{curr} > 0$ | Brand new topic emerging in public discourse |
  | `ACCELERATING` | $v > 0 \land a > 0$ | Rapidly growing discussion volume and momentum |
  | `PEAK` | $v > 0 \land a \le 0$ | Highest volume reached; growth rate starting to level |
  | `SUSTAINED` | $v \approx 0 \land \text{vol}_{curr} \ge 3$ | Stable, ongoing long-term conversation thread |
  | `DECAYING` | $v < 0$ | Discussion momentum declining |
  | `DORMANT` | $\text{vol}_{curr} = 0$ | Inactive discussion thread |

- **Cross-Temporal Sentiment Drift ($\Delta S$)**:
  $$\Delta S = \overline{\text{polarity}}_{curr} - \overline{\text{polarity}}_{prev}$$
- **Narrative Impact Score ($I_{narrative}$)**:
  $$I_{narrative} = \left( \text{post\_count} + \max(0, v) \times 1.5 \right) \times \left(1.0 + \min\left(3.0, \frac{\overline{E}}{100.0}\right)\right) \times \left(1.0 + 0.5 \times |\text{NSS}|\right)$$
- **Cross-Platform Narrative Distribution**:
  - Tracked per platform: post count, platform-specific engagement score, mean sentiment polarity, and platform share percentage of narrative posts.

---

### 3.5 Advanced Time-Series & Temporal Dynamics (Phase 4.6)

- **Interval Granularities**: `hour`, `day`, `week` (floored to UTC boundaries).
- **Temporal Moving Average Smoothing ($\text{SMA}_k$)**:
  $$\text{SMA}_k(i) = \frac{1}{\min(i+1, k)} \sum_{j=\max(0, i-k+1)}^{i} \text{metric}(j)$$
  Smoothes volume (`rolling_post_count_avg`), engagement (`rolling_engagement_avg`), and sentiment polarity (`rolling_sentiment_avg`) to reduce high-frequency sampling jitter.
- **Interval Velocity ($v_i$) & Acceleration ($a_i$)**:
  $$v_i = \text{metric}_i - \text{metric}_{i-1}, \quad a_i = v_i - v_{i-1}$$
  Calculated across consecutive discrete interval buckets for both volume and engagement.
- **Baseline vs. Current Window Analysis**:
  - Baseline Mean ($\overline{M}_{base}$) vs Current Mean ($\overline{M}_{curr}$).
  - InsightX Normalized Growth Rate ($\text{GR}_{\%}$):
    $$\text{GR}_{\%} = \frac{\overline{M}_{curr} - \overline{M}_{base}}{\max(|\overline{M}_{base}|, 1.0)} \times 100$$
    *(Documented as an InsightX analytical normalization heuristic)*.
- **Multi-Tiered Anomaly & Spike Detection**:
  Calculates standard deviation $z$-score relative to temporal distribution:
  $$z_i = \frac{\text{metric}_i - \mu}{\sigma}$$
  - `elevated`: $1.5 \le z_i < 2.0$
  - `anomalous`: $2.0 \le z_i < 3.0$
  - `extreme_spike`: $z_i \ge 3.0$
- **Cross-Platform Timeline Analysis**:
  Identifies platform chronology, earliest active platform, platform peak volumes/engagements, and platform volume share %.
- **Short-Term Trajectory Signal**:
  Deterministic rule-based classification based on trailing interval velocities and accelerations:
  - `rapidly_rising`: Trailing velocity $\ge 3.0$ and acceleration $> 0$.
  - `rising`: Trailing velocity $> 0$.
  - `rapidly_declining`: Trailing velocity $\le -3.0$ and acceleration $< 0$.
  - `declining`: Trailing velocity $< 0$.
  - `stable`: Velocity $\approx 0$.
  - `insufficient_data`: Sample size $< 2$ intervals.

---

## 4. Schemas Reference (`app/schemas/analytics_engine.py`)

- `IntervalUnit`: Enum (`hour`, `day`, `week`).
- `NarrativeLifecycleStage`: Enum (`emerging`, `accelerating`, `peak`, `sustained`, `decaying`, `dormant`).
- `EngagementScoreBreakdown`: Aggregated engagement counters, weighted scores, virality ratio, conversation depth, and impression rate.
- `EngagementDistribution`: Statistical score distribution (`min`, `max`, `mean`, `median`, `std_dev`, `p25`, `p75`).
- `PostEngagementProfile`: Individual post scorecard with engagement rates and outlier detection.
- `ViralityAnalytics`: Content amplification rate and count of high-virality posts.
- `DiscussionDepthAnalytics`: Conversational depth rate and count of active discussion threads.
- `PlatformEngagementComparison`: Cross-platform metrics, volume/engagement share %, and efficiency rank.
- `PlatformComparativeReport`: Comparative platform summary report identifying volume, engagement, viral, and discussion leaders.
- `DetailedEngagementReport`: Full multi-dimensional Phase 4.2 engagement scorecard.
- `PostSentimentProfile`: Per-post polarity score, label, confidence, text snippet, and lexical cue diagnostics.
- `SentimentDistributionSummary`: High-level sentiment distribution with positive/neutral/negative counts, percentages, average polarity, and Net Sentiment Score.
- `PlatformSentimentSummary`: Platform-partitioned sentiment profiles and net scores.
- `TemporalSentimentPoint`: Time-bucketed net sentiment tracker.
- `DetailedSentimentReport`: Comprehensive Phase 4.3 sentiment report with platform breakdowns, temporal trends, and extreme post extracts.
- `TrendMomentumMetrics`: Velocity, acceleration, growth rate %, momentum score, z-score, and direction classification.
- `TrendItemProfile`: Profile for tracked hashtag, topic, or keyword with sample post IDs and platform affiliations.
- `PlatformTrendSummary`: Platform-level trend rankings with top trends, spiking count, and emerging count.
- `DetailedTrendReport`: Comprehensive Phase 4.4 trend intelligence report ranking items by momentum score.
- `NarrativePlatformDistribution`: Platform-specific post count, engagement, polarity, and volume share percentage for a narrative.
- `NarrativeTrajectoryMetrics`: Narrative volume velocity, acceleration, engagement velocity, and sentiment drift.
- `NarrativeIntelligence`: Multi-dimensional narrative intelligence object combining topic identifiers, lifecycle stage, trajectory, sentiment distributions, engagement metrics, impact score, platform distribution, and representative post IDs.
- `DetailedNarrativeReport`: Comprehensive Phase 4.5 narrative analysis report with dominant, fastest-growing, highest-engagement, and cross-platform narrative collections.
- `TimeSeriesBucket`: Discrete temporal bucket with moving averages, velocity, acceleration, sentiment breakdown, platform distributions, and anomaly severity tiers.
- `TemporalBaselineComparison`: Comparative analysis comparing baseline historical period against current active observation window.
- `TemporalAnomalyDetail`: Detailed diagnostic entry for detected temporal spikes and anomalies.
- `PlatformTemporalSeries`: Platform-specific temporal volume, peak intervals, and growth rates.
- `CrossPlatformTemporalReport`: Cross-platform temporal presence, earliest platform, and peak volume/engagement platform leaders.
- `TemporalTrajectorySignal`: Heuristic rule-based short-term signal trajectory indicator with explainable rationale.
- `TemporalDynamicsReport`: Full Phase 4.6 temporal dynamics report combining buckets, baseline comparisons, detected anomalies, platform chronologies, trajectory signals, and temporal insights.
- `AnalyticsEngineAnalyzeRequest`: Comprehensive API request schema supporting pre-structured posts, raw posts, ad-hoc text, temporal bounds, platform filters, interval granularity, rolling window sizes, and top-k limits.
- `AnalyticsEngineCapabilitiesResponse`: Operational runtime metadata detailing active analytical engine subsystems, supported intervals, and API capabilities.
- `Phase4AnalyticsReport`: Comprehensive unified analytical result combining all dimensions with actionable textual summary insights.

---

## 5. Python API Usage Example

```python
from datetime import datetime, timezone
from app.services.analytics_engine import AnalyticsEngineService
from app.schemas.analytics_engine import IntervalUnit

# Instantiate the service
service = AnalyticsEngineService()

# Run unified analytics across posts (supports AnalyticsReadyPost, NormalizedPost, or dicts)
report = service.analyze(
    posts=posts,
    interval_unit=IntervalUnit.HOUR,
    rolling_window_size=3,
    anomaly_threshold_z=2.0
)

# Inspect high-level metrics
print(f"Evaluated posts: {report.total_posts_evaluated}")
print(f"Weighted Engagement: {report.engagement_analytics.weighted_engagement_score}")

# Inspect Phase 4.6 Advanced Time-Series Analytics
td = report.temporal_dynamics
print(f"Total Discrete Buckets: {td.total_buckets} ({td.interval_unit.value} interval)")
if td.baseline_comparison:
    print(f"Volume Growth vs Baseline: {td.baseline_comparison.volume_growth_rate_pct:+.1f}% ({td.baseline_comparison.direction})")
    print(f"Engagement Growth vs Baseline: {td.baseline_comparison.engagement_growth_rate_pct:+.1f}%")

if td.trajectory_signal:
    print(f"Near-Term Trajectory: {td.trajectory_signal.classification.upper()} ({td.trajectory_signal.explanation})")

if td.detected_anomalies:
    print(f"Detected Anomalies/Spikes: {len(td.detected_anomalies)}")
    for a in td.detected_anomalies:
        print(f" - [{a.severity.upper()}] {a.affected_metric}: z={a.z_score:.2f} ({a.description})")

if td.platform_temporal_comparison:
    cp = td.platform_temporal_comparison
    print(f"Earliest Platform: {cp.earliest_platform}, Peak Volume Platform: {cp.peak_volume_platform}")
```

---

## 6. Assumptions, Limitations & Future Extensions

### Current InsightX Capability (Deterministic Statistical & Heuristic Temporal Analytics):
- **Interval Aggregation**: Deterministic flooring to UTC boundaries (hour, day, week).
- **Smoothing**: Simple Moving Average ($\text{SMA}_k$) over configurable sliding windows.
- **Velocity & Acceleration**: Direct discrete difference heuristics ($v = M_t - M_{t-1}, a = v_t - v_{t-1}$).
- **Anomaly Detection**: Standard deviation $z$-score thresholding and moving-average deviation categorization.
- **Trajectory Signal**: Rule-based heuristic classification based on trailing velocity and acceleration; explicitly **not** an autoregressive or predictive ML model.

### Known Limitations:
- The trajectory signal does not perform complex multi-step time-series forecasting (e.g. ARIMA, Prophet, LSTM, or Transformer-based temporal forecasting).
- Anomaly detection assumes approximately unimodal baseline distributions and does not account for complex seasonal calendar effects (e.g. holiday patterns).

### Future Extensions:
- `BaseTimeSeriesEngine` interface is modular and decoupled from underlying algorithms, enabling future integration of probabilistic ML forecasting (e.g. NeuralProphet, Temporal Fusion Transformers) and unsupervised isolation forest anomaly models without altering downstream interfaces or `Phase4AnalyticsReport` schemas.

---

## 7. Phase 4.7 — Analytics API Layer

Phase 4.7 exposes the Analytics Engine capabilities through a clean, versioned, modular FastAPI interface mounted at `/api/v1/analytics/engine`.

### 7.1 Router & Endpoint Architecture

| Route | Method | Request Model | Response Model | Description |
|---|---|---|---|---|
| `/api/v1/analytics/engine/health` | `GET` | N/A | `dict` | Lightweight health check probe. |
| `/api/v1/analytics/engine/capabilities` | `GET` | N/A | `AnalyticsEngineCapabilitiesResponse` | Runtime engine capabilities, supported intervals, and versions. |
| `/api/v1/analytics/engine/analyze` | `POST` | `AnalyticsEngineAnalyzeRequest` | `Phase4AnalyticsReport` | Full multi-signal Analytics Engine pipeline execution. |
| `/api/v1/analytics/engine/engagement` | `POST` | `AnalyticsEngineAnalyzeRequest` | `DetailedEngagementReport` | Specialized engagement, virality, and distribution analysis. |
| `/api/v1/analytics/engine/sentiment` | `POST` | `AnalyticsEngineAnalyzeRequest` | `DetailedSentimentReport` | Specialized polarity, Net Sentiment Score, and drift analysis. |
| `/api/v1/analytics/engine/trends` | `POST` | `AnalyticsEngineAnalyzeRequest` | `DetailedTrendReport` | Specialized momentum, velocity, and spike trend analysis. |
| `/api/v1/analytics/engine/narratives` | `POST` | `AnalyticsEngineAnalyzeRequest` | `DetailedNarrativeReport` | Specialized narrative clustering, lifecycle, and impact analysis. |
| `/api/v1/analytics/engine/time-series` | `POST` | `AnalyticsEngineAnalyzeRequest` | `TemporalDynamicsReport` | Specialized temporal interval dynamics, smoothing, and anomalies. |

### 7.2 Request Model & Validation Rules

- **Flexible Input Sources**: Supports `posts` (pre-structured), `raw_posts` (automatically validated through `DataQualityService`), or `text` (ad-hoc single string).
- **Date Range Filtering**: `start_time` and `end_time` bounds (validated to ensure `start_time <= end_time`).
- **Platform Filtering**: `platform_filter` case-insensitive whitelist array.
- **Interval Granularity**: `interval_unit` enum (`hour`, `day`, `week`).
- **Smoothing & Outlier Limits**: `rolling_window_size` ($1 \le k \le 100$) and `anomaly_threshold_z` ($0 < z \le 10.0$).
- **Top-K Truncation**: `top_k` ($1 \le k \le 500$) to restrict ranked trend and narrative arrays.

### 7.3 Dependency Injection & Error Handling

- **Dependency Injection**: Uses FastAPI's `Depends(get_analytics_engine_service)` and `Depends(get_data_quality_service)` to maintain a clean singleton lifecycle without re-instantiating heavy services on each HTTP call.
- **Predictable Error Responses**:
  - `400 Bad Request`: Empty datasets, invalid timestamp ranges (`start_time > end_time`), or zero valid posts.
  - `422 Unprocessable Entity`: Invalid request payloads or schema constraint violations.
  - `500 Internal Server Error`: Sanitized generic error message with internal stack traces logged securely to prevent information leakage.

---

## 8. Test Suite & Quality Verification

Phase 4 tests cover:
- Engagement calculations, virality indices, amplification rates, conversation depth, and zero-division safety.
- Statistical distribution metrics (min, max, mean, median, standard deviation, quartiles Q1/Q3).
- Individual post scorecards and standard deviation outlier detection ($k \cdot \sigma$).
- Cross-platform comparative metrics, volume/engagement share %, and efficiency rankings.
- Per-post sentiment scoring, positive/neutral/negative classifications, and empty/None text safety.
- Sentiment distribution aggregation, platform partitioning, and temporal sentiment tracking.
- Trend momentum metrics, velocity, acceleration, growth rate %, and direction classifications.
- Hashtag/keyword extraction, volume spike detection, and emerging topic flagging.
- Platform-level trend summaries and cross-platform partitioning.
- Narrative identification, trajectory velocity and acceleration, engagement velocity, and cross-temporal sentiment drift.
- Narrative lifecycle classifications (`emerging`, `accelerating`, `peak`, `sustained`, `decaying`, `dormant`).
- Narrative impact scoring and ranking.
- Cross-platform narrative distributions and representative post ID extraction.
- Hourly, daily, and weekly discrete temporal bucketing and timestamp parsing.
- Moving-average smoothing across volume, engagement, and sentiment.
- Temporal velocity and acceleration calculations.
- Baseline vs. current comparison with growth rate percentage heuristics.
- Multi-tiered anomaly detection (`elevated`, `anomalous`, `extreme_spike`) and zero-variance robustness.
- Cross-platform temporal timeline analysis and chronology tracking.
- Deterministic heuristic trajectory classification (`rapidly_rising`, `rising`, `stable`, `declining`, `rapidly_declining`, `insufficient_data`).
- Temporal insight generation and full `AnalyticsEngineService` pipeline execution.
- Phase 4.7 API request validation, date range bounds, platform filtering, specialized endpoints, health/capabilities metadata, and sanitized 500 error handling.

### Verification Status:
- **Phase 4 Unit Tests**: 78 / 78 passing across `test_analytics_engine.py`, `test_trend_analytics_engine.py`, `test_narrative_analytics_engine.py`, `test_time_series_analytics_engine.py`, and `test_analytics_engine_api.py`.
- **Repository Total**: 375 / 375 passing (0 failures, 0 errors in 1.96s).
