# InsightX — Phase 4: Advanced Analytics Engine

## 1. Phase Overview & SIH PS 26152 Objective

Phase 4 establishes the high-level **Analytics Engine** for **InsightX**, synthesizing raw ingestion (Phase 2) and NLP signals (Phase 3) into holistic, multi-dimensional public intelligence for **Smart India Hackathon 2026 Problem Statement 26152 (Social Media Analytics)**.

While Phase 3 provides atomic NLP inferences (sentiment, emotion, topic clusters, demographics), Phase 4 introduces **dynamic synthesis across time, engagement depth, virality mechanics, sentiment distributions, and narrative lifecycles**.

---

## 2. Analytics Engine Architecture (Phase 4.1 – 4.3)

The Analytics Engine is structured into decoupled, modular components orchestrated by `AnalyticsEngineService`:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        Phase 4 Analytics Engine                         │
└────────────────────────────────────────────────────────────────────────┘
                                    │
       ┌────────────────────────────┼────────────────────────────┬────────────────────────────┐
       ↓                            ↓                            ↓                            ↓
┌──────────────┐             ┌──────────────┐             ┌──────────────┐             ┌──────────────┐
│  Engagement  │             │ Time-Series  │             │  Sentiment   │             │  Narrative   │
│    Engine    │             │   Dynamics   │             │    Engine    │             │   Dynamics   │
│ (Phase 4.2)  │             │ (Phase 4.1)  │             │ (Phase 4.3)  │             │ (Phase 4.1)  │
└──────────────┘             └──────────────┘             └──────────────┘             └──────────────┘
       │                            │                            │                            │
       │ • Weighted score           │ • Interval bucketing       │ • Per-post polarity        │ • Lifecycle stages
       │ • Virality & Amplification │ • k-period rolling avg     │ • Net sentiment score      │ • Velocity & accel.
       │ • Discussion depth         │ • Peak & anomaly z-score   │ • Distribution %           │ • Sentiment drift
       │ • Statistical distribution │ • Net sentiment track      │ • Platform sentiment       │ • Topic trajectories
       │ • Outlier post detection   └─────────────┬──────────────┴─────────────┬──────────────┘
       │ • Platform benchmarking                  │                            │
       └────────────────────────────┬─────────────┘                            │
                                    ↓                                          │
                 ┌──────────────────────────────────────┐                      │
                 │       AnalyticsEngineService         │◄─────────────────────┘
                 │   (Orchestrator & Insights Engine)   │
                 └──────────────────┬───────────────────┘
                                    ↓
                 ┌──────────────────────────────────────┐
                 │        Phase4AnalyticsReport         │
                 │   (Unified Multi-Signal Output)      │
                 └──────────────────────────────────────┘
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

### 3.3 Time-Series & Temporal Dynamics (Phase 4.1)
- **Interval Granularities**: `hour`, `day`, `week` (floored to UTC boundaries).
- **Rolling Moving Average ($\text{RMA}_k$)**:
  $$\text{RMA}_k(i) = \frac{1}{\min(i+1, k)} \sum_{j=\max(0, i-k+1)}^{i} \text{metric}(j)$$
- **Anomaly / Spike Z-Score**:
  $$z_i = \frac{volume_i - \mu_{volume}}{\sigma_{volume}}$$
  An interval is flagged as an anomaly when $z_i \ge \text{threshold}$ (default: $2.0\sigma$).

---

### 3.4 Narrative Lifecycle State Machine (Phase 4.1)
Topics and discussion threads progress across deterministic lifecycle stages based on temporal volume velocity ($v = \text{vol}_{curr} - \text{vol}_{prev}$) and acceleration ($a = v - \text{vol}_{prev}$):

| Lifecycle Stage | Condition | Description |
| :--- | :--- | :--- |
| `EMERGING` | $\text{vol}_{prev} = 0 \land \text{vol}_{curr} > 0$ | Brand new topic emerging in the public discourse |
| `ACCELERATING` | $v > 0 \land a > 0$ | Rapidly growing discussion volume and momentum |
| `PEAK` | $v > 0 \land a \le 0$ | Highest volume reached; growth rate starting to level |
| `SUSTAINED` | $v \approx 0 \land \text{vol}_{curr} \ge \text{threshold}$ | Stable, ongoing long-term conversation thread |
| `DECAYING` | $v < 0$ | Discussion momentum declining |
| `DORMANT` | $\text{vol}_{curr} = 0$ | Inactive discussion thread |

- **Cross-Temporal Sentiment Drift ($\Delta S$)**:
  $$\Delta S = \overline{\text{polarity}}_{curr} - \overline{\text{polarity}}_{prev}$$

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
    for plat, plat_sent in report.detailed_sentiment.platform_sentiment.items():
        print(f"[{plat}] Net Sentiment: {plat_sent.net_sentiment_score:+.2f} ({plat_sent.dominant_sentiment})")
```

---

## 6. Baseline Analyzer Capabilities & Known Limitations

### Capabilities:
- Fast, deterministic rule- and lexicon-based inference without external heavy dependencies.
- Emoji sentiment mapping and negation handling (e.g., "not bad", "never good").
- Capitalization intensifier booster (e.g., "EXCELLENT").
- Safe handling of empty text, missing values, and mixed language snippets.

### Known Limitations:
- The baseline analyzer utilizes lexicon rules rather than a heavy transformer-based LLM/BERT model.
- Complex sarcasm, deep domain irony, and context-dependent idiomatic expressions may default to neutral or base polarity.
- The interface `BaseSentimentAnalyticsEngine` is designed for modularity to allow drop-in replacement with transformer/fine-tuned embedding models in future phases without architectural changes.

---

## 7. Test Suite & Quality Verification

Phase 4 tests in `backend/tests/` cover:
- Engagement calculations, virality indices, amplification rates, conversation depth, and zero-division safety.
- Statistical distribution metrics (min, max, mean, median, standard deviation, quartiles Q1/Q3).
- Individual post scorecards and standard deviation outlier detection ($k \cdot \sigma$).
- Cross-platform comparative metrics, volume/engagement share %, and efficiency rankings.
- Per-post sentiment scoring, positive/neutral/negative classifications, and empty/None text safety.
- Sentiment distribution aggregation, platform partitioning, and temporal sentiment tracking.
- Time-series interval flooring (hour/day/week), rolling averages, and anomaly z-score thresholding.
- Narrative lifecycle transitions, trajectory modeling, and sentiment drift.
- Full `AnalyticsEngineService` pipeline execution and summary insight generation.

### Verification Status:
- **Phase 4 Unit Tests**: 34 / 34 passing.
- **Repository Total**: 331 / 331 passing (0 failures, 0 errors).
