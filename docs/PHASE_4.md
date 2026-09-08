# InsightX — Phase 4: Advanced Analytics Engine & Release Readiness

## 1. Phase Overview & SIH PS 26152 Objective

Phase 4 establishes the comprehensive **Analytics Engine** for **InsightX**, synthesizing raw multi-platform ingestion (Phase 2) and atomic NLP signals (Phase 3) into actionable, multi-dimensional public intelligence for **Smart India Hackathon 2026 Problem Statement 26152 (Social Media Analytics)**.

While Phase 3 provides atomic NLP inferences (sentiment, emotion, topic clusters, demographics), Phase 4 introduces **dynamic synthesis across time, engagement depth, virality mechanics, sentiment distributions, trend momentum, temporal acceleration, and evolving narrative lifecycles**.

---

## 2. End-to-End System Architecture

The Analytics Engine processes social media data through a strict, multi-stage pipeline designed for modularity, determinism, and high reproducibility:

```text
Raw Platform Data (Twitter/X, Reddit, Telegram, YouTube)
                      │
                      ▼
            DataNormalizer (Phase 2)
  [Canonical field mapping, metrics parsing, platform standardization]
                      │
                      ▼
          DataQualityService (Phase 3.1)
  [Unicode NFC normalization, entity extraction (#, @, URLs, emojis), validation]
                      │
                      ▼
         AnalyticsEngineService (Phase 4 Orchestrator)
                      │
     ┌────────────────┼────────────────┬────────────────┬────────────────┐
     ▼                ▼                ▼                ▼                ▼
┌──────────────┐┌──────────────┐┌──────────────┐┌──────────────┐┌──────────────┐
│  Engagement  ││  Sentiment   ││    Trend     ││  Narrative   ││ Time-Series  │
│    Engine    ││    Engine    ││    Engine    ││    Engine    ││   Dynamics   │
│ (Phase 4.2)  ││ (Phase 4.3)  ││ (Phase 4.4)  ││ (Phase 4.5)  ││ (Phase 4.6)  │
└──────┬───────┘└──────┬───────┘└──────┬───────┘└──────┬───────┘└──────┬───────┘
       │               │               │               │               │
       ▼               ▼               ▼               ▼               ▼
• Weighted score • Polarity     • Velocity      • Topic themes  • UTC buckets
• Virality index • Net score    • Acceleration  • 6-stage cycle • Rolling SMA
• Discussion     • Distributions• Momentum score• Drift delta   • Anomaly tiers
• Outliers (k*σ) • Drift points • Spike alerts  • Impact score  • Trajectory
       │               │               │               │               │
       └───────────────┼───────────────┴───────────────┼───────────────┘
                       ▼
             Phase4AnalyticsReport
   [Unified Multi-Signal Output & Natural Language Insights]
                       │
                       ▼
             Analytics API Layer (Phase 4.7)
       Mounted at: /api/v1/analytics/engine
```

### 2.1 Subsystem Responsibilities & Interactions

1. **`DataNormalizer` (Phase 2)**:
   - Ingests raw heterogeneous payloads from disparate social networks (X, Reddit, Telegram, YouTube).
   - Standardizes disparate metric fields (`favorites`/`retweets`/`upvotes`/`views`) into canonical fields (`likes`, `comments`, `shares`, `views`).
   - Resolves ISO-8601 timestamps and canonical platform identifiers.

2. **`DataQualityService` (Phase 3.1)**:
   - Performs Unicode NFC normalization, strips hazardous control characters, and parses entity tokens (`#hashtags`, `@mentions`, `emojis`, `urls`).
   - Filters out corrupt or unparseable records, delivering high-integrity `AnalyticsReadyPost` objects to downstream engines.

3. **`AnalyticsEngineService` (Orchestrator)**:
   - Manages singleton instances of all analytical engines through dependency injection (`get_analytics_engine_service`).
   - Resolves temporal window parameters, platform filters, and rolling statistical limits.
   - Concurrently delegates computation to specialized sub-engines without cross-subsystem coupling.
   - Synthesizes findings into natural-language summary insights and bundles the final `Phase4AnalyticsReport`.

4. **Specialized Engines (Phases 4.2 – 4.6)**:
   - **`EngagementEngine`**: Quantifies attention economics, interaction depths, and cross-platform benchmarks.
   - **`SentimentAnalyticsEngine`**: Measures collective sentiment polarity, Net Sentiment Scores, and temporal drift.
   - **`TrendAnalyticsEngine`**: Tracks volume momentum, growth velocities, and identifies sudden viral spikes.
   - **`NarrativeDynamicsEngine`**: Clusters conversational threads, models their lifecycle stage transitions, and calculates narrative impact.
   - **`TimeSeriesDynamicsEngine`**: Aggregates metrics into discrete temporal buckets, smooths sampling jitter with moving averages, categorizes multi-tiered anomalies, and identifies directional trajectory signals.

5. **API Layer (`/api/v1/analytics/engine`) (Phase 4.7)**:
   - Exposes RESTful HTTP endpoints for both unified reports and dedicated sub-engine queries.
   - Enforces strict Pydantic v2 input validation, bounds checks, and standardized error responses.

---

## 3. Analytics Methodology & Formulations

To ensure scientific rigor and transparent expectations, InsightX clearly distinguishes between:
- **Project-Specific Heuristics/Metrics**: Empirically tuned formulas designed for fast social intelligence.
- **Conventional Mathematical Concepts**: Standard statistical formulations (e.g., mean, median, standard deviation, percentiles, moving averages, z-scores).
- **Deterministic Baseline Implementations**: Rule-based algorithms that execute deterministically without external API dependencies.
- **Future Production/ML Improvements**: Deep learning and probabilistic modeling architectures planned for post-hackathon scaling.

---

### 3.1 Engagement & Virality Analytics (Phase 4.2)

Attention across social networks is asymmetric: a share reflects higher intent than a comment, which in turn reflects higher intent than a like.

#### Formulations:
- **Weighted Engagement Score ($E$)** *(InsightX Heuristic)*:
  $$E = (likes \times 1.0) + (comments \times 2.0) + (shares \times 3.0)$$
  *Rationale*: Reflects the escalating effort of user actions from passive appreciation (like) to active dialog (comment) to public endorsement/amplification (share).
- **Virality Index ($V$)** *(InsightX Ratio Heuristic)*:
  $$V = \frac{total\_shares}{\max(total\_likes, 1)}$$
  *Interpretation*: Measures amplification velocity relative to baseline post appreciation.
- **Amplification Rate ($AR$)** *(Conventional Ratio)*:
  $$AR = \frac{total\_shares}{\max(total\_interactions, 1)} \quad \text{where } total\_interactions = likes + comments + shares$$
- **Discussion Depth ($D$)** *(InsightX Ratio Heuristic)*:
  $$D = \frac{total\_comments}{\max(total\_likes, 1)}$$
  *Interpretation*: Identifies conversation-heavy vs. broadcast-heavy content.
- **Conversation Rate ($CR$)** *(Conventional Ratio)*:
  $$CR = \frac{total\_comments}{\max(total\_interactions, 1)}$$
- **Engagement Rate per Impression ($ER$)** *(Conventional Social Standard)*:
  $$ER = \frac{total\_likes + total\_comments + total\_shares}{\max(total\_views, 1)} \quad (\text{when } total\_views > 0)$$
- **Average Post Engagement ($\overline{E}$)** *(Conventional Math)*:
  $$\overline{E} = \frac{E}{total\_posts}$$
- **Statistical Score Distribution** *(Conventional Statistics)*:
  - Minimum, Maximum, Arithmetic Mean ($\mu$), Median ($50^{\text{th}}$ percentile).
  - Standard Deviation ($\sigma = \sqrt{\frac{1}{N}\sum (x_i - \mu)^2}$).
  - Quartiles: $25^{\text{th}}$ percentile ($Q_1$) and $75^{\text{th}}$ percentile ($Q_3$) via linear interpolation.
- **High-Engagement Outlier Detection** *(Conventional Statistical Heuristic)*:
  $$\text{Threshold}_{outlier} = \mu_{E} + (k \cdot \sigma_{E}) \quad (\text{default } k = 2.0\sigma)$$
  Posts exceeding this score are flagged as significant viral outliers.
- **Cross-Platform Benchmarking** *(Conventional Math)*:
  - $\text{Post Share \%} = \frac{N_{platform}}{N_{total}} \times 100$
  - $\text{Engagement Share \%} = \frac{E_{platform}}{E_{total}} \times 100$
  - **Efficiency Rank**: Platforms ordered descending by $\overline{E}_{platform}$ (Rank 1 = highest engagement yield per post).

---

### 3.2 Sentiment Analytics & Net Sentiment Score (Phase 4.3)

#### Formulations:
- **Per-Post Polarity Score ($s_i$)** *(Deterministic Lexical Baseline)*:
  $$s_i \in [-1.0, 1.0]$$
  Computed via the rule-based lexical analyzer evaluating token valence, emoji polarity, capitalization intensifiers, and negation modifiers (e.g., "not bad" vs. "bad").
- **Sentiment Classification ($label_i$)** *(Baseline Thresholding)*:
  $$label_i = \begin{cases} \text{positive} & \text{if } s_i > +0.05 \\ \text{negative} & \text{if } s_i < -0.05 \\ \text{neutral} & \text{otherwise} \end{cases}$$
- **Sentiment Distribution Percentages** *(Conventional Math)*:
  $$\text{Positive \%} = \frac{N_{pos}}{N_{total}} \times 100, \quad \text{Neutral \%} = \frac{N_{neu}}{N_{total}} \times 100, \quad \text{Negative \%} = \frac{N_{neg}}{N_{total}} \times 100$$
- **Net Sentiment Score ($\text{NSS}$)** *(Industry Standard Metric)*:
  $$\text{NSS} = \frac{N_{pos} - N_{neg}}{\max(N_{total}, 1)} \in [-1.0, 1.0]$$
  Provides a standardized index where $+1.0$ indicates unanimous positivity and $-1.0$ indicates unanimous negativity.
- **Platform Sentiment Partitioning**:
  $$\text{NSS}_{platform} = \frac{N_{pos, p} - N_{neg, p}}{\max(N_{total, p}, 1)}$$
- **Temporal Sentiment Point**:
  Continuous time-bucketed Net Sentiment Score and mean polarity tracking polarity drift across hours or days.

---

### 3.3 Trend Detection & Momentum Formulation (Phase 4.4)

Trend detection separates true dynamic surges from static baseline popularity by tracking velocity, acceleration, and engagement amplification.

#### Formulations:
- **Velocity ($v$)** *(Discrete Difference)*:
  $$v = \text{volume}_{current} - \text{volume}_{baseline}$$
- **Acceleration ($a$)** *(Discrete Difference)*:
  $$a = v - \text{volume}_{baseline} \quad (\text{when } \text{volume}_{baseline} > 0)$$
- **Growth Rate Percentage ($\text{GR}_{\%}$)** *(Conventional Percentage Growth)*:
  $$\text{GR}_{\%} = \begin{cases} \frac{\text{volume}_{current} - \text{volume}_{baseline}}{\text{volume}_{baseline}} \times 100 & \text{if } \text{volume}_{baseline} > 0 \\ \text{volume}_{current} \times 100 & \text{otherwise} \end{cases}$$
- **Engagement Amplification Factor ($F_{eng}$)** *(InsightX Heuristic)*:
  $$F_{eng} = 1.0 + \min\left(2.0, \frac{\overline{E}_{topic}}{100.0}\right)$$
  Boosts topics accompanied by high user engagement rather than passive bot activity (capped at 3.0x).
- **Growth Multiplier ($M_{growth}$)** *(InsightX Logarithmic Scale Heuristic)*:
  $$M_{growth} = \log_2\left(2.0 + \frac{\max(0, \text{GR}_{\%})}{100.0}\right)$$
  Dampens explosive linear growth to prevent runaway scores while rewarding exponential surges.
- **Momentum Score ($S_{momentum}$)** *(InsightX Composite Heuristic)*:
  $$S_{momentum} = \begin{cases} \text{volume}_{current} \times 2.5 \times M_{growth} \times F_{eng} & \text{if spiking} \\ \text{volume}_{current} \times 2.0 \times F_{eng} & \text{if emerging} \\ v \times M_{growth} \times F_{eng} & \text{if accelerating} \\ v \times \left(\frac{1}{\max(1.0, F_{eng})}\right) & \text{if declining} \\ \max(0.1, \text{volume}_{current} \times 0.1) & \text{if stable} \end{cases}$$
- **Trend Classifications**:
  - `emerging`: Baseline volume $= 0$ and current volume $> 0$.
  - `spiking`: Topic standard score $z \ge 2.0$, or ($\text{GR}_{\%} \ge 200\%$ with $\text{volume}_{current} \ge 3$).
  - `accelerating`: Velocity $> 0$ and acceleration $> 0$.
  - `declining`: Velocity $< 0$.
  - `stable`: Velocity $\approx 0$.

---

### 3.4 Narrative Analysis & Impact Scoring (Phase 4.5)

Narratives represent cohesive conversation themes evolving across time and platforms.

#### Formulations:
- **Narrative Lifecycle State Machine** *(Deterministic State Classification)*:
  Evaluates volume velocity ($v = \text{vol}_{curr} - \text{vol}_{prev}$) and acceleration ($a = v - \text{vol}_{prev}$):

  | Lifecycle Stage | Mathematical Condition | Behavioral Description |
  | :--- | :--- | :--- |
  | `EMERGING` | $\text{vol}_{prev} = 0 \land \text{vol}_{curr} > 0$ | Novel topic entering public discourse |
  | `ACCELERATING` | $v > 0 \land a > 0$ | Rapidly growing discussion volume and momentum |
  | `PEAK` | $v > 0 \land a \le 0$ | Peak volume reached; growth rate leveling off |
  | `SUSTAINED` | $v \approx 0 \land \text{vol}_{curr} \ge 3$ | Stable, ongoing long-term conversation thread |
  | `DECAYING` | $v < 0$ | Discussion momentum tapering downward |
  | `DORMANT` | $\text{vol}_{curr} = 0$ | Inactive conversation thread |

- **Cross-Temporal Sentiment Drift ($\Delta S$)** *(Conventional Delta)*:
  $$\Delta S = \overline{\text{polarity}}_{curr} - \overline{\text{polarity}}_{prev}$$
  Quantifies whether public mood around a narrative is becoming more positive ($\Delta S > 0$) or deteriorating ($\Delta S < 0$).
- **Narrative Impact Score ($I_{narrative}$)** *(InsightX Multi-Factor Heuristic)*:
  $$I_{narrative} = \left( \text{post\_count} + \max(0, v) \times 1.5 \right) \times \left(1.0 + \min\left(3.0, \frac{\overline{E}}{100.0}\right)\right) \times \left(1.0 + 0.5 \times |\text{NSS}|\right)$$
  *Rationale*: Synthesizes total volume, growth velocity, average audience engagement, and sentiment polarization (controversy factor).

---

### 3.5 Advanced Time-Series & Temporal Dynamics (Phase 4.6)

#### Formulations:
- **Interval Granularities**: `hour`, `day`, `week` (floored deterministically to UTC boundaries).
- **Simple Moving Average Smoothing ($\text{SMA}_k$)** *(Conventional Time-Series Smoothing)*:
  $$\text{SMA}_k(i) = \frac{1}{\min(i+1, k)} \sum_{j=\max(0, i-k+1)}^{i} \text{metric}(j)$$
  Smoothes volume (`rolling_post_count_avg`), engagement (`rolling_engagement_avg`), and polarity (`rolling_sentiment_avg`) over a configurable window ($1 \le k \le 100$).
- **Temporal Velocity ($v_i$) & Acceleration ($a_i$)** *(Discrete Differential Heuristics)*:
  $$v_i = \text{metric}_i - \text{metric}_{i-1}, \quad a_i = v_i - v_{i-1}$$
- **Baseline vs. Current Window Analysis**:
  Divides the temporal timeline by split ratio (default 0.5):
  $$\text{GR}_{\%} = \frac{\overline{M}_{curr} - \overline{M}_{base}}{\max(|\overline{M}_{base}|, 1.0)} \times 100$$
  *(InsightX analytical normalization heuristic protecting against division by zero).*
- **Multi-Tiered Anomaly & Spike Detection** *(Statistical Standard Score Heuristic)*:
  Calculates standard scores ($z$-scores) across discrete temporal buckets for volume ($z_v$) and engagement ($z_e$) relative to their timeline distribution:
  $$z_v = \frac{\text{post\_count} - \mu_{vol}}{\sigma_{vol}}, \quad z_e = \frac{\text{engagement\_score} - \mu_{eng}}{\sigma_{eng}}, \quad z_i = \max(z_v, z_e)$$
  - Severity Tiers (evaluated when $z_i \ge 1.5$):
    - `elevated`: $1.5 \le z_i < 2.0$ (noticeable volume or engagement elevation above historical window norm).
    - `anomalous`: $2.0 \le z_i < 3.0$ (statistically significant volume or engagement spike).
    - `extreme_spike`: $z_i \ge 3.0$ (severe outlier event requiring immediate operator attention).
  - Anomaly Flagging: A bucket is marked `is_anomaly = True` when $z_i \ge \text{anomaly\_threshold\_z}$ (configurable, default $2.0$).
  - Moving-Average Baseline Deviation: The diagnostic detail records `moving_avg_deviation = \text{actual} - \text{expected\_baseline}`, where `expected_baseline` is drawn from the Simple Moving Average $\text{SMA}_k$ (`rolling_post_count_avg` or `rolling_engagement_avg`), or window mean if unavailable.
- **Short-Term Trajectory Signal** *(Deterministic Rule-Based Classifier)*:
  Evaluates trailing interval velocities and accelerations:
  - `rapidly_rising`: Trailing velocity $\ge 3.0$ and acceleration $> 0$.
  - `rising`: Trailing velocity $> 0$.
  - `rapidly_declining`: Trailing velocity $\le -3.0$ and acceleration $< 0$.
  - `declining`: Trailing velocity $< 0$.
  - `stable`: Velocity $\approx 0$.
  - `insufficient_data`: Sample size $< 2$ discrete intervals.
  *(Documented as an explainable heuristic signal, explicitly not an autoregressive ML model).*

---

## 4. Analytics REST API Specification (Phase 4.7)

Mounted on FastAPI at route prefix `/api/v1/analytics/engine`.

### 4.1 Endpoints Overview

| Method | Endpoint | Request Body | Response Model | Description |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/health` | None | `dict` | Operational health status probe. |
| `GET` | `/capabilities` | None | `AnalyticsEngineCapabilitiesResponse` | Runtime metadata on active engines, supported intervals, and capabilities. |
| `POST` | `/analyze` | `AnalyticsEngineAnalyzeRequest` | `Phase4AnalyticsReport` | Full multi-signal Analytics Engine pipeline execution. |
| `POST` | `/engagement` | `AnalyticsEngineAnalyzeRequest` | `DetailedEngagementReport` | Specialized engagement profiles, virality indices, and platform breakdowns. |
| `POST` | `/sentiment` | `AnalyticsEngineAnalyzeRequest` | `DetailedSentimentReport` | Specialized polarity, Net Sentiment Score, and temporal drift. |
| `POST` | `/trends` | `AnalyticsEngineAnalyzeRequest` | `DetailedTrendReport` | Specialized trend detection, momentum scores, and spike anomalies. |
| `POST` | `/narratives` | `AnalyticsEngineAnalyzeRequest` | `DetailedNarrativeReport` | Specialized narrative clustering, 6-stage lifecycles, and impact scoring. |
| `POST` | `/time-series` | `AnalyticsEngineAnalyzeRequest` | `TemporalDynamicsReport` | Specialized temporal interval dynamics, moving averages, and anomalies. |

---

### 4.2 Request Model (`AnalyticsEngineAnalyzeRequest`)

Defined in `app.schemas.analytics_engine.py`:

```python
class AnalyticsEngineAnalyzeRequest(BaseModel):
    # Input Sources (At least one must be provided)
    posts: Optional[List[Any]] = Field(default=None, description="Pre-structured post representations")
    raw_posts: Optional[List[Union[RawPostPayload, Dict[str, Any]]]] = Field(default=None, description="Raw platform posts for pipeline validation")
    text: Optional[str] = Field(default=None, description="Ad-hoc text string for instant analysis")

    # Optional Context & Topic Models
    topics: Optional[List[Union[ExtractedTopic, Dict[str, Any]]]] = Field(default=None, description="Topic models from Phase 3.4")

    # Temporal Configuration
    interval_unit: Optional[IntervalUnit] = Field(default=IntervalUnit.HOUR, description="hour | day | week")
    reference_time: Optional[datetime] = Field(default=None, description="Reference baseline timestamp")
    start_time: Optional[datetime] = Field(default=None, description="Filter start bound (UTC)")
    end_time: Optional[datetime] = Field(default=None, description="Filter end bound (UTC)")

    # Filtering & Aggregation Limits
    platform_filter: Optional[List[str]] = Field(default=None, description="Case-insensitive platform whitelist")
    rolling_window_size: Optional[int] = Field(default=3, ge=1, le=100, description="Moving-average window (k)")
    anomaly_threshold_z: Optional[float] = Field(default=2.0, gt=0.0, le=10.0, description="Anomaly z-score cutoff")
    top_k: Optional[int] = Field(default=10, ge=1, le=500, description="Truncate ranked trend/narrative arrays")
```

#### Validation Behavior & Error Responses:
- **Empty Dataset Handling (API vs. Service)**:
  - *API Boundary Validation*: At the HTTP route level, requests providing an explicitly empty post list (`"posts": []` or `"raw_posts": []`) return `400 Bad Request` with detail `"Empty post list provided for analysis."`. Similarly, omitting all input fields returns `400 Bad Request` with `"No post content provided for analysis. Please provide 'posts', 'raw_posts', or 'text'."`. This protects API resources from processing no-op requests.
  - *Service-Level Robustness*: In contrast, direct invocation of `AnalyticsEngineService.analyze(posts=[])` safely produces a structured, zeroed `Phase4AnalyticsReport` (`total_posts_evaluated: 0`, zero engagement/temporal metrics, and `summary_insights: ["No posts provided for analysis."]`). Likewise, if valid posts are submitted to the API but filtered out by `platform_filter` or time bounds, the service gracefully executes and returns an empty report without raising exceptions.
- **Timestamp Ranges**: Returns `400 Bad Request` with detail `"start_time cannot be after end_time."` if `start_time > end_time`.
- **Constraint Violations**: Returns `422 Unprocessable Entity` for malformed payloads, invalid ISO timestamps, out-of-bounds `rolling_window_size` ($< 1$ or $> 100$), or `top_k` ($< 1$ or $> 500$).
- **Internal Errors**: Returns `500 Internal Server Error` with a sanitized message while logging internal stack traces securely.

---

### 4.3 Capabilities Response Model (`AnalyticsEngineCapabilitiesResponse`)

```json
{
  "engine_version": "4.7.0",
  "supported_interval_units": ["hour", "day", "week"],
  "active_subsystems": [
    "engagement",
    "sentiment",
    "trends",
    "narratives",
    "time_series"
  ],
  "capabilities": [
    "multi_platform_synthesis",
    "weighted_engagement_scoring",
    "virality_and_discussion_analytics",
    "lexicon_sentiment_and_nss",
    "trend_velocity_and_momentum",
    "narrative_lifecycle_tracking",
    "temporal_moving_average_smoothing",
    "tiered_anomaly_detection",
    "cross_platform_benchmarking",
    "summary_insight_generation"
  ],
  "operational_status": "ready"
}
```

---

## 5. API Usage Examples

### 5.1 Comprehensive Multi-Platform Analysis Request

#### `POST /api/v1/analytics/engine/analyze`
```json
{
  "raw_posts": [
    {
      "platform": "twitter",
      "external_id": "tw_101",
      "text": "Huge public protest erupts over the new urban metro transit fare hike! Outrageous! #MetroFares #TransitCrisis",
      "author_username": "citizen_voice",
      "author_display_name": "Citizen Voice",
      "posted_at": "2026-09-08T10:00:00Z",
      "language": "en",
      "metrics": { "likes": 250, "comments": 80, "shares": 110, "views": 4500 }
    },
    {
      "platform": "reddit",
      "external_id": "rd_102",
      "text": "Detailed breakdown of the urban metro transit fare restructuring policy and budget deficit. #MetroFares",
      "author_username": "transit_analyst",
      "author_display_name": "Transit Analyst",
      "posted_at": "2026-09-08T11:00:00Z",
      "language": "en",
      "metrics": { "likes": 180, "comments": 95, "shares": 30, "views": 3200 }
    },
    {
      "platform": "telegram",
      "external_id": "tg_103",
      "text": "Community organizing update: Peaceful rally planned at City Hall regarding #TransitCrisis tomorrow at 10 AM.",
      "author_username": "urban_action",
      "author_display_name": "Urban Action",
      "posted_at": "2026-09-08T12:00:00Z",
      "language": "en",
      "metrics": { "likes": 90, "comments": 25, "shares": 40, "views": 1800 }
    },
    {
      "platform": "youtube",
      "external_id": "yt_104",
      "text": "Watch our live interview with city transit officials explaining the new fare schedule and future improvements.",
      "author_username": "city_news_live",
      "author_display_name": "City News Live",
      "posted_at": "2026-09-08T13:00:00Z",
      "language": "en",
      "metrics": { "likes": 340, "comments": 60, "shares": 25, "views": 6000 }
    }
  ],
  "interval_unit": "hour",
  "rolling_window_size": 3,
  "anomaly_threshold_z": 2.0,
  "top_k": 5
}
```

### 5.2 Representative Response Structure

```json
{
  "total_posts_evaluated": 4,
  "analyzed_at": "2026-09-08T14:00:00Z",
  "time_window_start": "2026-09-08T10:00:00Z",
  "time_window_end": "2026-09-08T13:00:00Z",
  "engagement_analytics": {
    "total_posts": 4,
    "total_likes": 860,
    "total_comments": 260,
    "total_shares": 205,
    "total_views": 15500,
    "weighted_engagement_score": 1995.0,
    "virality_index": 0.2384,
    "discussion_depth": 0.3023,
    "engagement_rate_per_impression": 0.085484,
    "average_post_engagement": 498.75
  },
  "virality_analytics": {
    "virality_index": 0.2384,
    "amplification_rate": 0.1547,
    "shares_per_post": 51.25,
    "high_virality_posts_count": 0
  },
  "discussion_depth": {
    "discussion_depth": 0.3023,
    "conversation_rate": 0.1962,
    "comments_per_post": 65.0,
    "high_discussion_posts_count": 1
  },
  "platform_comparative": {
    "platforms": {
      "twitter": {
        "platform": "twitter",
        "total_posts": 1,
        "post_share_pct": 25.0,
        "engagement_share_pct": 37.09,
        "weighted_engagement_score": 740.0,
        "avg_engagement_per_post": 740.0,
        "virality_index": 0.44,
        "discussion_depth": 0.32,
        "engagement_rate_per_impression": 0.097778,
        "efficiency_rank": 1
      },
      "youtube": {
        "platform": "youtube",
        "total_posts": 1,
        "post_share_pct": 25.0,
        "engagement_share_pct": 26.82,
        "weighted_engagement_score": 535.0,
        "avg_engagement_per_post": 535.0,
        "virality_index": 0.0735,
        "discussion_depth": 0.1765,
        "engagement_rate_per_impression": 0.070833,
        "efficiency_rank": 2
      }
    },
    "top_volume_platform": "twitter",
    "top_engaging_platform": "twitter",
    "top_viral_platform": "twitter",
    "top_discussion_platform": "reddit"
  },
  "sentiment_distribution": {
    "total_evaluated": 4,
    "positive_count": 1,
    "neutral_count": 2,
    "negative_count": 1,
    "positive_percentage": 25.0,
    "neutral_percentage": 50.0,
    "negative_percentage": 25.0,
    "average_polarity": 0.025,
    "net_sentiment_score": 0.0,
    "dominant_sentiment": "neutral"
  },
  "trends": [
    {
      "term": "#metrofares",
      "item_type": "hashtag",
      "display_name": "#metrofares",
      "momentum": {
        "current_volume": 2,
        "baseline_volume": 0,
        "growth_rate_pct": 200.0,
        "velocity": 2.0,
        "acceleration": 2.0,
        "momentum_score": 24.0,
        "z_score": 0.0,
        "direction": "emerging"
      },
      "post_ids": ["tw_101", "rd_102"],
      "platforms": ["twitter", "reddit"]
    }
  ],
  "narratives": [
    {
      "topic_id": "transit_fare_protests",
      "topic_label": "Transit Fare Protests",
      "lifecycle_stage": "emerging",
      "trajectory": {
        "current_volume": 4,
        "previous_volume": 0,
        "volume_velocity": 4.0,
        "volume_acceleration": 4.0,
        "current_engagement": 1995.0,
        "engagement_velocity": 1995.0,
        "sentiment_drift": 0.0
      },
      "impact_score": 59.85,
      "dominant_sentiment": "neutral",
      "platforms": ["twitter", "reddit", "telegram", "youtube"],
      "representative_post_ids": ["tw_101", "rd_102", "yt_104"]
    }
  ],
  "temporal_dynamics": {
    "total_buckets": 4,
    "interval_unit": "hour",
    "buckets": [
      {
        "bucket_start": "2026-09-08T10:00:00Z",
        "bucket_end": "2026-09-08T11:00:00Z",
        "post_count": 1,
        "engagement_score": 740.0,
        "rolling_post_count_avg": 1.0,
        "rolling_engagement_avg": 740.0,
        "velocity": null,
        "acceleration": null,
        "is_anomaly": false,
        "anomaly_severity": "normal"
      }
    ],
    "trajectory_signal": {
      "classification": "rising",
      "recent_velocity": 1.0,
      "recent_acceleration": 0.0,
      "confidence_score": 0.8,
      "explanation": "Signal is trending upward with recent positive volume velocity (+1.0)."
    },
    "detected_anomalies": [],
    "insights": [
      "Temporal timeline spans 4 discrete hour intervals.",
      "Earliest activity originated on twitter.",
      "Peak volume occurred at 2026-09-08 10:00:00+00:00 with 1 posts."
    ]
  },
  "summary_insights": [
    "Evaluated 4 posts across 4 platforms with total weighted engagement of 1,995.0.",
    "Top platform by post volume is twitter (25.0% of all activity).",
    "Net Sentiment Score is +0.00 with neutral public posture.",
    "Fastest emerging narrative: Transit Fare Protests (Stage: emerging, Impact Score: 59.85)."
  ]
}
```

### 5.3 Empty & Sparse Dataset Behavior

The system distinguishes between direct Python service handling and API gateway contract enforcement:

1. **Direct Service Handling (`AnalyticsEngineService.analyze(posts=[])`)**:
   Calling the engine service directly with an empty list does not fail or crash. It safely returns a structured, zeroed `Phase4AnalyticsReport` with `total_posts_evaluated: 0`, empty breakdowns, and `summary_insights: ["No posts provided for analysis."]`. Furthermore, if an API request contains valid posts that are subsequent filtered out by `platform_filter` or temporal bounds, the engine executes normally and returns this clean zeroed report.

2. **HTTP API Gateway Rejection**:
   To prevent frivolous client requests, the REST API boundary validates incoming payloads and explicitly rejects requests providing empty collections or omitting all content:

#### Empty Post List Request:
```json
{
  "posts": []
}
```
**HTTP Response**: `400 Bad Request`
```json
{
  "detail": "Empty post list provided for analysis."
}
```

#### Missing Input Request:
```json
{
  "interval_unit": "day"
}
```
**HTTP Response**: `400 Bad Request`
```json
{
  "detail": "No post content provided for analysis. Please provide 'posts', 'raw_posts', or 'text'."
}
```

### 5.4 Invalid Request & Bounds Violations

#### Reversed Timestamp Range:
```json
{
  "text": "Valid test post content",
  "start_time": "2026-09-10T00:00:00Z",
  "end_time": "2026-09-08T00:00:00Z"
}
```
**HTTP Response**: `400 Bad Request`
```json
{
  "detail": "start_time cannot be after end_time."
}
```

#### Out-of-Bounds Rolling Window:
```json
{
  "text": "Valid test post content",
  "rolling_window_size": 250
}
```
**HTTP Response**: `422 Unprocessable Entity`
```json
{
  "detail": [
    {
      "type": "less_than_equal",
      "loc": ["body", "rolling_window_size"],
      "msg": "Input should be less than or equal to 100",
      "input": 250,
      "ctx": { "le": 100 }
    }
  ]
}
```

---

## 6. Reproducibility & Developer Runbook

### 6.1 Environment Setup

```bash
# 1. Clone repository and navigate to backend directory
cd InsightX/backend

# 2. Activate Python 3.12+ virtual environment
source .venv/bin/activate

# 3. Verify installed dependencies
pip install -r requirements.txt
```

### 6.2 Running the Application

```bash
# Start the FastAPI server with live-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
- **OpenAPI Interactive Documentation (Swagger UI)**: `http://localhost:8000/docs`
- **ReDoc Alternative Documentation**: `http://localhost:8000/redoc`
- **OpenAPI JSON Schema**: `http://localhost:8000/openapi.json`

### 6.3 Running Test Suites

```bash
# Run the complete test suite (391 tests)
.venv/bin/python -m unittest discover -s tests -p "test_*.py"

# Run Phase 4 Integration & Quality Hardening tests (16 tests)
.venv/bin/python -m unittest tests/test_phase4_integration.py

# Run Phase 4 Analytics API Layer tests (22 tests)
.venv/bin/python -m unittest tests/test_analytics_engine_api.py

# Run Phase 4 Engine Unit Tests
.venv/bin/python -m unittest tests/test_analytics_engine.py
.venv/bin/python -m unittest tests/test_trend_analytics_engine.py
.venv/bin/python -m unittest tests/test_narrative_analytics_engine.py
.venv/bin/python -m unittest tests/test_time_series_analytics_engine.py

# Run Pre-Phase 4 Test Baselines
.venv/bin/python -m unittest tests/test_api.py
.venv/bin/python -m unittest tests/test_analytics_api.py
.venv/bin/python -m unittest tests/test_integration.py
.venv/bin/python -m unittest tests/test_reliability.py
```

### 6.4 Codebase Directory Map

The analytical engine components reside cleanly in `backend/app/services/analytics_engine/`:

```text
backend/app/
├── api/
│   └── routes/
│       ├── analytics.py             # Phase 3 NLP API routes
│       └── analytics_engine.py      # Phase 4.7 Analytics Engine API routes
├── schemas/
│   └── analytics_engine.py          # Phase 4 Pydantic v2 data models & contracts
└── services/
    └── analytics_engine/
        ├── __init__.py              # Service exports & dependency providers
        ├── base.py                  # Abstract base classes (ABC) for all engines
        ├── engagement.py            # Phase 4.2 Engagement & Virality Engine
        ├── sentiment.py             # Phase 4.3 Sentiment & NSS Analytics Engine
        ├── trend.py                 # Phase 4.4 Trend & Momentum Analytics Engine
        ├── narrative.py             # Phase 4.5 Narrative Dynamics Engine
        ├── time_series.py           # Phase 4.6 Advanced Time-Series Dynamics Engine
        └── service.py               # Orchestrator & Natural Language Insights Engine
```

---

## 7. Limitations, Assumptions & Future Improvements

To maintain technical integrity and transparent evaluation during SIH 2026, InsightX explicitly documents the architectural scope and baseline assumptions of the current implementation:

1. **Deterministic Rule-Based Sentiment Baseline**:
   - *Current*: Utilizes an enhanced lexicon analyzer with emoji parsing, negation modifiers, and capitalization handling.
   - *Limitation*: Sarcasm, deep context-dependent idioms, and code-mixed vernacular (e.g., Hinglish) may default to neutral polarity.
   - *Future Roadmap*: Fine-tune transformer-based multilingual models (e.g., `xlm-roberta-base` or `IndicBERT`) behind `BaseSentimentEngine`.

2. **Heuristic Keyword & Token Topic Grouping**:
   - *Current*: Clusters content using token co-occurrence, entity annotations, and hashtag extraction.
   - *Limitation*: Lacks semantic synonym understanding (e.g., recognizing that "fare hike" and "ticket price increase" belong to the same narrative without overlapping tokens).
   - *Future Roadmap*: Integrate dense vector embeddings (e.g., Sentence-BERT) with HDBSCAN/UMAP clustering behind `BaseNarrativeEngine`.

3. **Heuristic Momentum & Impact Scoring**:
   - *Current*: Composite mathematical formulas combining volume differences, logarithmic multipliers, engagement coefficients, and polarity factors.
   - *Limitation*: Formula weights are calibrated for typical public feed distributions rather than dynamically learned per community.
   - *Future Roadmap*: Train a supervised ranking model using historical virality ground truth.

4. **Synchronous In-Memory API Execution**:
   - *Current*: HTTP requests execute synchronously in-memory, returning unified intelligence reports within milliseconds for batches up to 1,000 posts.
   - *Limitation*: Very large historical datasets ($> 50,000$ posts) processed synchronously could exceed standard HTTP gateway timeouts.
   - *Future Roadmap*: Deploy a distributed worker queue (Celery + Redis) for asynchronous batch jobs, with polling or Webhook delivery.

5. **Empirical Development Sanity Checks**:
   - *Current*: Empirical benchmarks demonstrate $< 0.15\text{s}$ execution for 1,000 posts on standard hardware as a regression guard.
   - *Limitation*: These benchmarks verify absence of algorithmic regressions, not formal O(N) guarantees under high network concurrency.
   - *Future Roadmap*: Dedicated load testing with Locust or k6 under simulated SIH hackathon concurrency.

---

## 8. Smart India Hackathon (SIH 2026) Demonstration Guide

InsightX is built specifically to address **Problem Statement 26152: Social Media Analytics**. During the SIH presentation, Phase 4 enables a comprehensive, live, end-to-end intelligence demonstration:

```text
Raw Multi-Platform Social Stream (Twitter, Reddit, Telegram, YouTube)
                              ↓
              Unified Multi-Signal Analytics
                              ↓
       ┌──────────────────────┼──────────────────────┐
       ▼                      ▼                      ▼
Engagement Depth     Sentiment Polarization     Trend Momentum
(Attention Economics) (Net Sentiment Score)    (Emerging vs Spiking)
       │                      │                      │
       └──────────────────────┼──────────────────────┘
                              ▼
                Narrative Lifecycle Tracking
               (Emerging → Peak → Sustained)
                              ↓
                  Temporal Anomaly Alerting
                   (Standard Score Spikes)
                              ↓
           Actionable Natural Language Insights
```

### Demonstration Script & Practical Value:

1. **Step 1: Multi-Platform Ingestion (`POST /analyze`)**:
   - Submit a live, heterogeneous payload representing a developing public event (e.g., public transit fare changes or civic infrastructure updates).
   - Show that InsightX seamlessly consumes disparate data models from Twitter/X, Reddit, Telegram, and YouTube simultaneously.

2. **Step 2: Attention Economics & Virality (`engagement_analytics`)**:
   - Demonstrate that InsightX looks beyond raw like counts.
   - Highlight the **Virality Index** (shares/likes) and **Discussion Depth** (comments/likes) to reveal whether a topic is generating passive viewing, intense debate, or active public dissemination.
   - Point out **Cross-Platform Benchmarks**: show which platform is the primary amplifier vs. discussion forum.

3. **Step 3: Sentiment & Polarization (`sentiment_distribution`)**:
   - Present the **Net Sentiment Score (NSS)** to give evaluators an immediate gauge of net public favorability ($+1.0$ to $-1.0$).
   - Show that InsightX isolates platform-specific sentiment variations (e.g., positive YouTube broadcast vs. critical Reddit commentary).

4. **Step 4: Trend Momentum vs. Raw Volume (`trends`)**:
   - Highlight how InsightX distinguishes an **emerging** trend from a static high-volume topic.
   - Explain the **Momentum Score**, showing how velocity, acceleration, and engagement factors isolate genuine viral surges.

5. **Step 5: Narrative Lifecycle & Impact (`narratives`)**:
   - Show the 6-stage lifecycle classifier transitioning a conversation from `EMERGING` to `ACCELERATING` to `PEAK`.
   - Review the **Narrative Impact Score**, demonstrating how government agencies or brand managers can prioritize which civic narratives require immediate public response.

6. **Step 6: Temporal Behavior & Outlier Alerts (`temporal_dynamics`)**:
   - Display discrete hourly/daily buckets with rolling average smoothing.
   - Highlight automated **Anomaly Detection** alerting on statistical spikes ($z \ge 2.0$, or configurable cutoff) and categorizing severity into elevated ($1.5 \le z < 2.0$), anomalous ($2.0 \le z < 3.0$), and extreme spikes ($z \ge 3.0$) without requiring manual threshold configuration.

7. **Step 7: Actionable Human-Readable Insights (`summary_insights`)**:
   - Highlight the executive summary bullet points automatically generated by the engine, translating complex mathematical distributions into clear, concise decisions.

---

## 9. Verification & Quality Assurance Matrix

| Test Module | Tests | Focus Area | Status |
| :--- | :---: | :--- | :---: |
| `test_analytics_engine.py` | 18 | Engagement formulas, virality index, outlier detection, platform rankings | **PASS** |
| `test_trend_analytics_engine.py` | 14 | Trend velocity, acceleration, growth rates, momentum scores, directions | **PASS** |
| `test_narrative_analytics_engine.py` | 15 | Narrative clustering, 6 lifecycle stages, sentiment drift, impact scores | **PASS** |
| `test_time_series_analytics_engine.py` | 15 | Temporal bucketing, moving averages, anomaly tiers, trajectory signals | **PASS** |
| `test_analytics_engine_api.py` | 22 | REST endpoints, parameter defaults, contract validation, error cases | **PASS** |
| `test_phase4_integration.py` | 16 | E2E multi-platform pipelines, consistency, determinism, performance sanity | **PASS** |
| **Phase 4 Subtotal** | **100** | **Complete Phase 4 Analytics Engine Suite** | **PASS** |
| Pre-Phase 4 Baselines (Phases 1–3) | 291 | Ingestion, normalizers, DB models, Phase 3 NLP engines, APIs | **PASS** |
| **Repository Total** | **391** | **Full InsightX Integration & Regression Test Suite** | **PASS** |

All **391 tests pass in ~2.2s** with 0 failures and 0 errors.
