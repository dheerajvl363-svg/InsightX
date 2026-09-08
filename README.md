# InsightX — Social Media Analytics Platform

Smart India Hackathon 2026 — Problem Statement 26152: **Social Media Analytics**

InsightX is an intelligent social media intelligence platform that turns real-time and batch public social-media streams into actionable public insights. It provides an automated analytics pipeline capable of multi-platform data normalization, quality sanitization, sentiment analysis, emotion recognition, topic clustering, narrative velocity/trend tracking, and privacy-preserving demographic intelligence.

---

## Current Status: Phase 4 Complete (Release Ready)

- **Phase 1 (Backend & Database Foundation)**: FastAPI, PostgreSQL, SQLAlchemy ORM models, health monitoring.
- **Phase 2 (Data Ingestion & Normalization)**: Platform adapters (X, Reddit, Telegram, YouTube), `DataNormalizer`, PostgreSQL storage, engagement metrics tracking.
- **Phase 3 (NLP Analytics Platform Foundation)**:
  - **3.1 Data Quality**: Unicode NFC normalization, entity extraction (`#hashtags`, `@mentions`, `emojis`, `urls`), quality filtering, `AnalyticsReadyPost`.
  - **3.2 Sentiment Analysis**: Lexicon-based polarity scoring and classification (`positive`, `neutral`, `negative`).
  - **3.3 Emotion Analysis**: Ekman 7-class emotion detection (`joy`, `sadness`, `anger`, `fear`, `surprise`, `disgust`, `neutral`) with confidence distributions.
  - **3.4 Topic & Narrative Extraction**: Unsupervised keyword and n-gram clustering.
  - **3.5 Trend Detection**: Temporal sliding window velocity tracking, percentage growth rates, statistical z-scores, trajectory classifications.
  - **3.6 Demographic Intelligence**: Age-group, gender, and geographic aggregation with k-anonymity privacy suppression (`min_group_size`).
  - **3.7 Analytics REST API**: Multi-layer orchestration via `POST /api/v1/analytics/analyze`.
- **Phase 4 (Advanced Analytics Engine & Release Readiness)**: Complete ([docs/PHASE_4.md](docs/PHASE_4.md)).
  - **4.1 Architecture & Base Engines**: Abstract base classes and orchestrator pattern (`AnalyticsEngineService`).
  - **4.2 Engagement & Virality**: Weighted scoring ($E$), virality index ($V$), discussion depth ($D$), statistical distributions, outlier detection ($k \cdot \sigma$), and cross-platform benchmarking.
  - **4.3 Sentiment & Net Sentiment Score**: Per-post polarity, Net Sentiment Score ($\text{NSS} \in [-1, 1]$), platform partitioning, and continuous temporal tracking.
  - **4.4 Trend & Momentum Analytics**: Volume velocity, acceleration, growth rate %, engagement factor, momentum scoring, and spike classifications.
  - **4.5 Narrative Dynamics**: Thematic clustering, 6-stage lifecycle state machine (`emerging`, `accelerating`, `peak`, `sustained`, `decaying`, `dormant`), sentiment drift ($\Delta S$), and narrative impact scoring.
  - **4.6 Advanced Time-Series**: Discrete temporal bucketing (hour, day, week), moving averages ($\text{SMA}_k$), baseline vs. current window comparison, multi-tier anomaly detection (`elevated`, `anomalous`, `extreme_spike`), and short-term trajectory signals.
  - **4.7 Analytics Engine REST API**: Modular API router mounted at `/api/v1/analytics/engine/*` with specialized and unified endpoints.
  - **4.8 Integration & Hardening**: End-to-end multi-platform integration, cross-component consistency, edge-case resilience, determinism, and performance sanity guards.
  - **4.9 Documentation & Release Readiness**: 391 unit, integration, and contract tests passing with 0 failures and 0 errors.

---

## System Architecture

```text
Platform Data (X / Reddit / Telegram / YouTube)
                        ↓
                 RawPostPayload
                        ↓
                 DataNormalizer
                        ↓
                 NormalizedPost
                        ↓
             DataQualityService (3.1)
                        ↓
               AnalyticsReadyPost
                        ↓
        ┌───────────────┼───────────────┐
        ↓               ↓               ↓
┌──────────────┐┌──────────────┐┌──────────────┐
│  Phase 3.2   ││  Phase 3.3   ││  Phase 3.4   │
│  Sentiment   ││   Emotion    ││ Topic/Narr.  │
│   Analysis   ││   Analysis   ││  Extraction  │
└──────────────┘└──────────────┘└──────┬───────┘
        │               │              │
        │               │       BatchTopicResult
        │               │              ↓
        │               │       ┌──────────────┐
        │               │       │  Phase 3.5   │
        │               │       │    Trend     │
        │               │       │   Analysis   │
        │               │       └──────┬───────┘
        │               │              │
        └───────┬───────┴──────────────┘
                ↓
┌────────────────────────────────────────────────────────┐
│  Phase 3.6: DemographicAnalysisService                 │
│  (Consumes Posts + Topics + Sentiment + Trends)        │
└────────────────────────────────────────────────────────┘
                        ↓
┌────────────────────────────────────────────────────────┐
│  Phase 3.7: Unified Analytics API                      │
│  POST /api/v1/analytics/analyze                        │
└────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```text
InsightX/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── analytics.py    # Analytics REST API (Phase 3.7)
│   │   │   │   ├── ingestion.py    # Ingestion endpoints (Phase 2)
│   │   │   │   └── __init__.py
│   │   ├── models/                 # SQLAlchemy ORM models (Post, User, Metric, Topic)
│   │   ├── schemas/                # Pydantic v2 schemas
│   │   │   ├── analytics_api.py    # CombinedAnalyzeRequest, CombinedAnalyticsResponse
│   │   │   ├── data_quality.py     # AnalyticsReadyPost, BatchDataQualityResult
│   │   │   ├── demographic.py      # DemographicDistribution, BatchDemographicResult
│   │   │   ├── emotion.py          # EmotionResult, BatchEmotionResult
│   │   │   ├── post.py             # RawPostPayload, NormalizedPost
│   │   │   ├── sentiment.py        # SentimentResult, BatchSentimentResult
│   │   │   ├── topic.py            # ExtractedTopic, BatchTopicResult
│   │   │   └── trend.py            # TopicTrendResult, BatchTrendResult
│   │   ├── services/
│   │   │   ├── adapters/           # X, Reddit, Telegram, YouTube adapters
│   │   │   ├── data_quality.py     # Data Quality & sanitization
│   │   │   ├── demographic/        # Demographic Intelligence engine & service
│   │   │   ├── emotion/            # Emotion Analysis engine & service
│   │   │   ├── normalizer.py       # DataNormalizer service
│   │   │   ├── sentiment/          # Sentiment Analysis engine & service
│   │   │   ├── topic/              # Topic Extraction engine & service
│   │   │   └── trend/              # Trend Detection engine & service
│   │   ├── database.py             # Database engine & session
│   │   └── main.py                 # FastAPI application
│   ├── tests/                      # Full test suite (297 tests)
│   │   ├── test_integration.py     # End-to-end integration tests
│   │   ├── test_reliability.py     # Robustness, boundary & performance tests
│   │   └── test_*.py               # Unit tests
│   └── requirements.txt
├── docs/                           # Documentation
│   ├── PHASE_1.md                  # Phase 1 documentation
│   ├── PHASE_3.md                  # Phase 3 technical documentation
│   └── PHASE_4.md                  # Phase 4 Advanced Analytics Engine documentation
└── README.md
```

---

## Analytics API Endpoints

### Base URL: `http://localhost:8000`

#### Phase 4 Analytics Engine Endpoints (Mounted at `/api/v1/analytics/engine`)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/analytics/engine/health` | Analytics Engine health check probe |
| `GET` | `/api/v1/analytics/engine/capabilities` | Runtime metadata on active engines, supported intervals, and capabilities |
| `POST` | `/api/v1/analytics/engine/analyze` | Full multi-signal Analytics Engine pipeline report (`Phase4AnalyticsReport`) |
| `POST` | `/api/v1/analytics/engine/engagement` | Specialized engagement profiles, virality indices, and platform breakdowns |
| `POST` | `/api/v1/analytics/engine/sentiment` | Specialized polarity distributions, Net Sentiment Score, and temporal drift |
| `POST` | `/api/v1/analytics/engine/trends` | Specialized trend detection, momentum scores, and spike anomalies |
| `POST` | `/api/v1/analytics/engine/narratives` | Specialized narrative clustering, 6-stage lifecycles, and impact scoring |
| `POST` | `/api/v1/analytics/engine/time-series` | Specialized temporal interval dynamics, moving averages, and anomalies |

#### Phase 3 Foundation Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Core service health probe |
| `GET` | `/db-health` | PostgreSQL database connection probe |
| `POST` | `/api/v1/analytics/sentiment` | Batch/text sentiment polarity & classification |
| `POST` | `/api/v1/analytics/emotion` | 7-class discrete emotion detection |
| `POST` | `/api/v1/analytics/topics` | Unsupervised keyword and topic clustering |
| `POST` | `/api/v1/analytics/trends` | Temporal velocity and trend trajectory classification |
| `POST` | `/api/v1/analytics/demographics` | Age, gender, and location demographic breakdown |
| `POST` | `/api/v1/analytics/analyze` | Unified multi-layer Phase 3 analytics orchestration |

---

## Example Unified Analytics Request

### `POST /api/v1/analytics/analyze`

```json
{
  "raw_posts": [
    {
      "platform": "X",
      "external_id": "hyd_metro_001",
      "text": "Hyderabad metro rail fares increased drastically today! Completely outrageous! #MetroFares",
      "author_username": "daily_commuter",
      "author_display_name": "Daily Commuter",
      "posted_at": "2026-09-08T11:45:00Z",
      "language": "en",
      "metrics": {
        "likes": 120,
        "shares": 45,
        "comments": 22
      },
      "metadata": {
        "demographics": {
          "age": 24,
          "gender": "female",
          "city": "Hyderabad",
          "country": "India"
        }
      }
    },
    {
      "platform": "Reddit",
      "external_id": "ai_tech_002",
      "text": "Excited about new artificial intelligence technology and machine learning models research.",
      "author_username": "ai_researcher",
      "author_display_name": "AI Researcher",
      "posted_at": "2026-09-08T11:50:00Z",
      "language": "en",
      "metrics": {
        "likes": 85,
        "shares": 18,
        "comments": 14
      },
      "metadata": {
        "demographics": {
          "age": 29,
          "gender": "male",
          "city": "Bengaluru",
          "country": "India"
        }
      }
    }
  ],
  "reference_time": "2026-09-08T12:00:00Z",
  "window_duration_seconds": 3600,
  "include_sentiment": true,
  "include_emotion": true,
  "include_topics": true,
  "include_trends": true,
  "include_demographics": true
}
```

---

## Developer Runbook

### 1. Environment Setup & Server Run
```bash
# Navigate to backend directory
cd backend

# Activate virtual environment
source .venv/bin/activate

# Install dependencies if needed
pip install -r requirements.txt

# Start the application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Running Test Suite
```bash
# Run complete test suite (391 tests)
.venv/bin/python -m unittest discover -s tests -p "test_*.py"

# Run Phase 4 end-to-end integration & quality hardening tests
.venv/bin/python -m unittest tests/test_phase4_integration.py

# Run Phase 4 analytics engine API tests
.venv/bin/python -m unittest tests/test_analytics_engine_api.py

# Run end-to-end integration tests only
.venv/bin/python -m unittest tests/test_integration.py

# Run reliability & stress tests only
.venv/bin/python -m unittest tests/test_reliability.py
```

### 3. Git Quality & Repository Check
```bash
# Verify no trailing whitespace or diff issues
git diff --check

# Check repository state
git status
```

---

## Known Limitations & Current Assumptions

1. **Language Scope**: Sentiment and emotion engines are rule-based and optimized primarily for English text; multilingual posts default to neutral if English tokens are missing.
2. **Heuristic Topic Clustering**: Topic extraction relies on statistical keyword and n-gram co-occurrence; deep transformer embeddings (BERT/RoBERTa) are scheduled for future enhancement.
3. **Temporal Trend Windowing**: Trend detection calculates trajectory against the provided historical window; multi-year macroeconomic seasonality is not modeled.
4. **Explicit Demographics Only**: Demographics strictly aggregate explicit, authorized user metadata; the engine intentionally does not infer sensitive traits from raw text to preserve privacy.
5. **Public Stream Unknown Coverage**: In raw public feeds where user metadata is sparse, unknown demographic coverage will naturally be high.
6. **In-Memory Analytics Pipeline**: The `POST /analyze` route computes multi-layer analytics in-memory for the incoming batch and returns responses immediately; long-term analytics warehousing is not automatically triggered.
7. **Security Scope**: OAuth2/JWT authentication and IP-based rate limiting are not active in Phase 3.
