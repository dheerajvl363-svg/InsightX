# InsightX — Phase 4: Advanced Analytics Engine

## 1. Phase Overview & SIH PS 26152 Objective

Phase 4 establishes the high-level **Analytics Engine** for **InsightX**, synthesizing raw ingestion (Phase 2) and NLP signals (Phase 3) into holistic, multi-dimensional public intelligence for **Smart India Hackathon 2026 Problem Statement 26152 (Social Media Analytics)**.

While Phase 3 provides atomic NLP inferences (sentiment, emotion, topic clusters, demographics), Phase 4 introduces **dynamic synthesis across time, engagement depth, virality mechanics, and narrative lifecycles**.

---

## 2. Phase 4.1 Analytics Engine Architecture

The Analytics Engine is structured into four core decoupled components orchestrated by `AnalyticsEngineService`:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        Phase 4 Analytics Engine                         │
└────────────────────────────────────────────────────────────────────────┘
                                    │
       ┌────────────────────────────┼────────────────────────────┐
       ↓                            ↓                            ↓
┌──────────────┐             ┌──────────────┐             ┌──────────────┐
│  Engagement  │             │ Time-Series  │             │  Narrative   │
│    Engine    │             │   Dynamics   │             │   Dynamics   │
│ (4.1 Module) │             │ (4.1 Module) │             │ (4.1 Module) │
└──────────────┘             └──────────────┘             └──────────────┘
       │                            │                            │
       │ • Weighted score           │ • Interval bucketing       │ • Lifecycle stages
       │ • Virality index           │ • k-period rolling avg     │ • Velocity & accel.
       │ • Discussion depth         │ • Peak & anomaly z-score   │ • Sentiment drift
       │ • Platform breakdown       │ • Net sentiment track      │ • Topic trajectories
       └────────────────────────────┼────────────────────────────┘
                                    ↓
                 ┌──────────────────────────────────────┐
                 │       AnalyticsEngineService         │
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

### 3.1 Engagement & Virality Formulation
- **Weighted Engagement Score ($E$)**:
  $$E = (likes \times 1.0) + (comments \times 2.0) + (shares \times 3.0)$$
- **Virality Index ($V$)**:
  $$V = \frac{total\_shares}{\max(total\_likes, 1)}$$
- **Discussion Depth ($D$)**:
  $$D = \frac{total\_comments}{\max(total\_likes, 1)}$$
- **Engagement Rate per Impression ($ER$)**:
  $$ER = \frac{total\_likes + total\_comments + total\_shares}{\max(total\_views, 1)} \quad (\text{when } total\_views > 0)$$
- **Average Post Engagement ($\overline{E}$)**:
  $$\overline{E} = \frac{E}{total\_posts}$$

### 3.2 Time-Series & Temporal Dynamics
- **Interval Granularities**: `hour`, `day`, `week` (floored to UTC boundaries).
- **Rolling Moving Average ($\text{RMA}_k$)**:
  $$\text{RMA}_k(i) = \frac{1}{\min(i+1, k)} \sum_{j=\max(0, i-k+1)}^{i} \text{metric}(j)$$
- **Anomaly / Spike Z-Score**:
  $$z_i = \frac{volume_i - \mu_{volume}}{\sigma_{volume}}$$
  An interval is flagged as an anomaly when $z_i \ge \text{threshold}$ (default: $2.0\sigma$).

### 3.3 Narrative Lifecycle State Machine
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
- `TimeSeriesBucket`: Discrete temporal bucket containing volume, engagement, rolling averages, sentiment/emotion aggregates, and anomaly score.
- `TemporalDynamicsReport`: Full series of time buckets, peak interval indicators, and anomalous spike counts.
- `NarrativeTrajectoryMetrics`: Velocity, acceleration, engagement velocity, and sentiment drift.
- `NarrativeIntelligence`: Topic identification, representative keywords, post counts, lifecycle stage, trajectory metrics, and sample post IDs.
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
print(f"Virality Index: {report.engagement_analytics.virality_index}")
print(f"Peak Volume: {report.temporal_dynamics.peak_bucket_volume}")

# Inspect narrative lifecycles
for narrative in report.narratives:
    print(f"[{narrative.lifecycle_stage.value.upper()}] {narrative.label} (Posts: {narrative.post_count})")
```

---

## 6. Test Suite & Quality Verification

Phase 4.1 includes an isolated test suite in `backend/tests/test_analytics_engine.py` covering:
- Engagement calculations, virality indices, zero-division safety, and platform breakdowns.
- Time-series timestamp parsing, interval flooring (hour/day/week), rolling averages, and anomaly z-score thresholding.
- Narrative lifecycle transitions, trajectory modeling, and sentiment drift.
- Full `AnalyticsEngineService` pipeline execution and summary insight generation.

### Verification Status:
- **Phase 4.1 Unit Tests**: 15 / 15 passing.
- **Repository Total**: 312 / 312 passing (0 failures, 0 errors).
