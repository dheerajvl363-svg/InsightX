# InsightX — Phase 4: Advanced Analytics Engine

## 1. Phase Overview & SIH PS 26152 Objective

Phase 4 establishes the high-level **Analytics Engine** for **InsightX**, synthesizing raw ingestion (Phase 2) and NLP signals (Phase 3) into holistic, multi-dimensional public intelligence for **Smart India Hackathon 2026 Problem Statement 26152 (Social Media Analytics)**.

While Phase 3 provides atomic NLP inferences (sentiment, emotion, topic clusters, demographics), Phase 4 introduces **dynamic synthesis across time, engagement depth, virality mechanics, sentiment distributions, trend momentum, and evolving narrative lifecycles**.

---

## 2. Analytics Engine Architecture (Phase 4.1 – 4.5)

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
│ (Phase 4.2)  │             │ (Phase 4.1)  ││ (Phase 4.3)  ││ (Phase 4.4)  │             │ (Phase 4.5)  │
└──────────────┘             └──────────────┘└──────────────┘└──────────────┘             └──────────────┘
       │                            │               │               │                            │
       │ • Weighted score           │ • Bucketing   │ • Polarity    │ • Mining/Spikes            │ • Lifecycle stages
       │ • Virality & Amplification │ • Moving avg  │ • Net score   │ • Momentum score           │ • Velocity & accel.
       │ • Discussion depth         │ • Anomaly z   │ • Dist %      │ • Direction classification │ • Sentiment drift
       │ • Score distribution       │ • Trends      │ • Platform    │ • Platform summaries       │ • Impact score
       │ • Platform benchmarking    └───────┬───────┴───────┬───────┴────────────┬───────────────┤ • Multi-platform
       └────────────────────────────────────┴───────────────┤                    │               └──────┬───────┘
                                                            ↓                    ↓                      │
                                         ┌──────────────────────────────────────────────┐               │
                                         │            AnalyticsEngineService            │◄──────────────┘
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

### 3.5 Time-Series & Temporal Dynamics (Phase 4.1)
- **Interval Granularities**: `hour`, `day`, `week` (floored to UTC boundaries).
- **Rolling Moving Average ($\text{RMA}_k$)**:
  $$\text{RMA}_k(i) = \frac{1}{\min(i+1, k)} \sum_{j=\max(0, i-k+1)}^{i} \text{metric}(j)$$
- **Anomaly / Spike Z-Score**:
  $$z_i = \frac{volume_i - \mu_{volume}}{\sigma_{volume}}$$
  An interval is flagged as an anomaly when $z_i \ge \text{threshold}$ (default: $2.0\sigma$).

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

# Inspect Phase 4.3 Sentiment Analytics
if report.detailed_sentiment:
    dist = report.detailed_sentiment.overall_distribution
    print(f"Net Sentiment Score: {dist.net_sentiment_score:+.2f}")
    print(f"Dominant Sentiment: {dist.dominant_sentiment}")

# Inspect Phase 4.4 Trend Analytics
if report.detailed_trends:
    print(f"Total Trends Evaluated: {report.detailed_trends.total_trends_evaluated}")
    for trend in report.detailed_trends.ranked_trends[:3]:
        print(f"[{trend.item_type}] {trend.name}: Score={trend.momentum.momentum_score:.2f} ({trend.momentum.direction})")

# Inspect Phase 4.5 Narrative Analytics
if report.detailed_narratives:
    dom = report.detailed_narratives.dominant_narrative
    if dom:
        print(f"Dominant Narrative: {dom.label} (Impact Score: {dom.narrative_impact_score:.1f}, Stage: {dom.lifecycle_stage.value})")
        print(f"Sentiment Drift: {dom.trajectory.sentiment_drift:+.2f}, Net Sentiment: {dom.net_sentiment_score:+.2f}")
        for plat, p_dist in dom.platform_breakdown.items():
            print(f" - [{plat}] {p_dist.post_count} posts ({p_dist.share_percentage:.1f}%)")
```

---

## 6. Assumptions, Limitations & Future Extensions

### Baseline Assumptions:
- Narrative clustering in baseline mode uses explicit topic associations (from Phase 3.4 TopicEngine), topic annotations, hashtags, or fallback rule-based term extraction.
- Deterministic lifecycle rules model volume velocity and acceleration relative to a temporal midpoint split or explicit reference time.

### Known Limitations:
- Simple keyword or hashtag grouping does not capture deep semantic nuance or polysemous conversational context.
- Without dense neural embeddings, sub-narratives with disparate phrasing may be clustered into separate baseline buckets.

### Future Extensions:
- `BaseNarrativeEngine` is designed as an extensible abstract interface. In future phases, dense vector embeddings (e.g. sentence transformers, HDBSCAN clustering) can be dropped in without changing downstream consumers or the `Phase4AnalyticsReport` structure.

---

## 7. Test Suite & Quality Verification

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
- Full `AnalyticsEngineService` pipeline execution and summary insight generation.

### Verification Status:
- **Phase 4 Unit Tests**: 54 / 54 passing across `test_analytics_engine.py`, `test_trend_analytics_engine.py`, and `test_narrative_analytics_engine.py`.
- **Repository Total**: 351 / 351 passing (0 failures, 0 errors).
