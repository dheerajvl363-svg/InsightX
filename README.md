# InsightX — Social Media Analytics Platform

Smart India Hackathon 2026 — Problem Statement 26152: **Social Media Analytics**

InsightX is an intelligent social media analytics and intelligence platform that turns real-time and batch public social-media streams into actionable public intelligence. It provides an automated analytics pipeline capable of multi-platform data normalization, quality sanitization, sentiment analysis, emotion recognition, topic clustering, narrative velocity/trend tracking, co-occurrence network graphs, privacy-preserving demographic intelligence, and a high-performance REST API.

---

## Current Status: Phase 5 Complete (Backend Release Ready)

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
- **Phase 5 (FastAPI REST API, OpenAPI Documentation & Release Readiness)**: Complete ([docs/PHASE_5.md](docs/PHASE_5.md)).
  - **5.1 API Foundation**: App lifecycle lifespan, versioned routing (`/api/v1`), app metadata, system health probes.
  - **5.2 Schemas & Validation**: Strict Pydantic v2 schemas for all request/response models with field validation.
  - **5.3 Analytics Endpoints & Network Analysis**: High-level platform, engagement, time-series, author, topic, sentiment, and co-occurrence hashtag/mention network graph endpoints.
  - **5.4 Posts, Platforms & Timeline REST API**: Filtered and paginated posts (`/api/v1/posts`), post lookup by ID (`/api/v1/posts/{id}`), platform discovery (`/api/v1/platforms`), and time-bucketed post timeline (`/api/v1/timeline`).
  - **5.5 Combined Analytics & Dashboard API**: Unified overview endpoint (`/api/v1/analytics/overview`) powering frontend executive KPI cards and visualizations.
  - **5.6 Standardized Error Handling**: Global exception handlers returning standard `ErrorResponse` schema (400, 404, 422, 500) without internal trace or SQL leakages.
  - **5.7 API Testing & Hardening**: Hardened parameter boundaries, pagination edge cases, and query validations.
  - **5.8 OpenAPI Documentation**: Complete OpenAPI 3.1.0 specification with rich tags, descriptions, examples, and interactive Swagger UI / ReDoc.
  - **5.9 Release Readiness**: Configurable CORS middleware, `.env.example` template, zero-leak production defaults, live startup verification, and 561 passing tests.

---

## Interactive API Documentation

When the backend is running, interactive API documentation is available at:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI Schema (JSON)**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

---

## System Architecture

```text
Browser / Frontend Client (Phase 6: Next.js / Vite / React)
                           │
                           ▼  [HTTP / JSON]
           ┌───────────────────────────────┐
           │      CORSMiddleware           │  <-- Configurable allowed origins
           └──────────────┬────────────────┘
                          ▼
           ┌───────────────────────────────┐
           │  Global Exception Handlers    │  <-- Standardized 400/404/422/500 JSON
           └──────────────┬────────────────┘
                          ▼
           ┌───────────────────────────────┐
           │     FastAPI Router System     │
           └──────────────┬────────────────┘
                          │
     ┌────────────────────┼────────────────────┬────────────────────┐
     ▼                    ▼                    ▼                    ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐
│    Health    │   │ Posts & Data │   │  Analytics   │   │ Ingestion & Base │
│   Endpoints  │   │  & Timeline  │   │  Dashboard   │   │  Analytics Engine│
│ (/api/v1/..) │   │ (/api/v1/..) │   │ (/api/v1/..) │   │   (/api/v1/..)   │
└──────┬───────┘   └──────┬───────┘   └──────┬───────┘   └────────┬─────────┘
       │                  │                  │                    │
       ▼                  ▼                  ▼                    ▼
  Config / DB       SQLAlchemy ORM     AnalyticsEngine     DataNormalizer /
 Connectivity       (SessionLocal)        Services         Quality Pipeline
```

---

## Directory Structure

```text
InsightX/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── errors.py           # Global exception handlers (Phase 5.6)
│   │   │   ├── routes/
│   │   │   │   ├── analytics.py    # High-level analytics & network endpoints (Phase 5.3)
│   │   │   │   ├── analytics_engine.py # Low-level Analytics Engine API (Phase 4.7)
│   │   │   │   ├── health.py       # Versioned health probe (Phase 5.1)
│   │   │   │   ├── ingestion.py    # Raw post ingestion API (Phase 2)
│   │   │   │   ├── platforms.py    # Platform discovery API (Phase 5.4)
│   │   │   │   ├── posts.py        # Filtered & paginated post API (Phase 5.4)
│   │   │   │   ├── timeline.py     # Time-bucketed volume API (Phase 5.4)
│   │   │   │   └── __init__.py
│   │   ├── models/                 # SQLAlchemy ORM models (Post, User, Metric, Topic)
│   │   ├── schemas/                # Pydantic v2 schemas
│   │   │   ├── analytics.py        # PostSummary, PostListResponse, count & query schemas
│   │   │   ├── analytics_api.py    # CombinedAnalyzeRequest, CombinedAnalyticsResponse
│   │   │   ├── common.py           # ErrorDetail, ErrorResponse, HealthResponse
│   │   │   ├── dashboard.py        # OverviewResponse, TopicSummary, TrendSummary
│   │   │   ├── data_quality.py     # AnalyticsReadyPost, BatchDataQualityResult
│   │   │   ├── demographic.py      # DemographicDistribution, BatchDemographicResult
│   │   │   ├── emotion.py          # EmotionResult, BatchEmotionResult
│   │   │   ├── platforms.py        # PlatformInfo, PlatformListResponse
│   │   │   ├── post.py             # RawPostPayload, NormalizedPost
│   │   │   ├── sentiment.py        # SentimentResult, BatchSentimentResult
│   │   │   ├── timeline.py         # TimelineBucket, TimelineResponse
│   │   │   ├── topic.py            # ExtractedTopic, BatchTopicResult
│   │   │   └── trend.py            # TopicTrendResult, BatchTrendResult
│   │   ├── services/
│   │   │   ├── adapters/           # X, Reddit, Telegram, YouTube adapters
│   │   │   ├── analytics/          # Advanced Analytics Engines (Phase 4.1–4.6)
│   │   │   ├── data_quality.py     # Data Quality & sanitization (Phase 3.1)
│   │   │   ├── demographic/        # Demographic Intelligence engine & service (Phase 3.6)
│   │   │   ├── emotion/            # Emotion Analysis engine & service (Phase 3.3)
│   │   │   ├── ingestion.py        # Ingestion service & batch processor (Phase 2)
│   │   │   ├── normalizer.py       # DataNormalizer service (Phase 2)
│   │   │   ├── sentiment/          # Sentiment Analysis engine & service (Phase 3.2)
│   │   │   ├── topic/              # Topic Extraction engine & service (Phase 3.4)
│   │   │   └── trend/              # Trend Detection engine & service (Phase 3.5)
│   │   ├── config.py               # Environment configuration & CORS resolution
│   │   ├── database.py             # Database engine & session management
│   │   ├── exceptions.py           # Domain exceptions
│   │   └── main.py                 # FastAPI application definition & middleware
│   ├── data/
│   │   └── mock_posts.json         # Realistic multi-platform mock posts dataset
│   ├── scripts/
│   │   ├── init_db.py              # Database schema initialization script
│   │   └── load_mock_data.py       # Ingests mock data through normalization pipeline
│   ├── tests/                      # Full test suite (561 tests)
│   │   ├── test_phase5_*.py        # Phase 5 API, schema, error & OpenAPI tests
│   │   ├── test_phase4_*.py        # Phase 4 engine integration tests
│   │   ├── test_integration.py     # End-to-end integration tests
│   │   ├── test_reliability.py     # Robustness, boundary & performance tests
│   │   └── test_*.py               # Unit tests
│   ├── .env.example                # Safe environment variable configuration template
│   └── requirements.txt
├── docs/                           # Technical Specifications
│   ├── PHASE_1.md                  # Phase 1: Foundation & Database
│   ├── PHASE_3.md                  # Phase 3: NLP Analytics Platform Foundation
│   ├── PHASE_4.md                  # Phase 4: Advanced Analytics Engine
│   └── PHASE_5.md                  # Phase 5: REST API, OpenAPI & Release Readiness
└── README.md
```

---

## Core API Endpoint Groups

### 1. Health & Readiness (`tags=["Health"]`)
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Core service health probe (`{"status": "ok"}`) |
| `GET` | `/db-health` | PostgreSQL connectivity probe |
| `GET` | `/api/v1/health` | Detailed version, environment, and subsystem status |

### 2. Posts & Content Discovery (`tags=["Posts"]`)
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/posts` | Paginated post filtering by platform, sentiment, keyword, metrics, date |
| `GET` | `/api/v1/posts/{post_id}` | Detailed single post retrieval by ID |

### 3. Platforms & Timeline (`tags=["Platforms", "Timeline"]`)
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/platforms` | Supported platform metadata, active post counts, capabilities |
| `GET` | `/api/v1/timeline` | Time-series post volume aggregated into hour/day/week intervals |

### 4. High-Level Analytics & Dashboard (`tags=["Analytics"]`)
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/analytics/overview` | Unified multi-signal dashboard summary (KPIs, platforms, sentiment, trends) |
| `GET` | `/api/v1/analytics/posts` | Paginated posts matching analytical filters |
| `GET` | `/api/v1/analytics/count` | Fast count of posts matching filters |
| `GET` | `/api/v1/analytics/platforms` | Total post volume and engagement by platform |
| `GET` | `/api/v1/analytics/platforms/compare` | Cross-platform comparative benchmark across metrics and sentiment |
| `GET` | `/api/v1/analytics/languages` | Language distribution of analyzed posts |
| `GET` | `/api/v1/analytics/engagement` | Aggregated engagement metrics and engagement rates |
| `GET` | `/api/v1/analytics/timeseries` | Time-series volume distributions |
| `GET` | `/api/v1/analytics/timeseries/engagement` | Time-series engagement momentum tracking |
| `GET` | `/api/v1/analytics/authors` | High-impact author leaderboards |
| `GET`/`POST` | `/api/v1/analytics/topics` | Extracted keyword clusters and thematic topics |
| `GET`/`POST` | `/api/v1/analytics/sentiment` | Sentiment distribution and Net Sentiment Score ($\text{NSS}$) |
| `POST` | `/api/v1/analytics/emotion` | Ekman 7-class emotion classification |
| `GET`/`POST` | `/api/v1/analytics/trends` | Trending topics with velocity, acceleration, and spike detection |
| `POST` | `/api/v1/analytics/demographics` | Privacy-preserving demographic aggregations (k-anonymity) |
| `GET`/`POST` | `/api/v1/analytics/network` | Hashtag and user-mention co-occurrence graph (nodes and weighted edges) |
| `POST` | `/api/v1/analytics/analyze` | Unified in-memory multi-signal orchestration |

### 5. Ingestion Pipeline (`tags=["Ingestion"]`)
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/ingestion/posts` | Ingest a single raw social media post |
| `POST` | `/api/v1/ingestion/posts/batch` | Batch ingest posts with deduplication |
| `GET` | `/api/v1/ingestion/platforms` | Discover supported platform adapters |

### 6. Low-Level Analytics Engine (`tags=["Analytics Engine"]`)
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/analytics/engine/health` | Analytics Engine health probe |
| `GET` | `/api/v1/analytics/engine/capabilities` | Runtime metadata on active engines |
| `POST` | `/api/v1/analytics/engine/analyze` | Full multi-signal Analytics Engine report |
| `POST` | `/api/v1/analytics/engine/engagement` | Engagement profiles, virality indices, outlier detection |
| `POST` | `/api/v1/analytics/engine/sentiment` | Polarity distributions, Net Sentiment Score, temporal drift |
| `POST` | `/api/v1/analytics/engine/trends` | Trend detection, momentum scores, spike anomalies |
| `POST` | `/api/v1/analytics/engine/narratives` | Narrative clustering, 6-stage lifecycles, impact scoring |
| `POST` | `/api/v1/analytics/engine/time-series` | Temporal interval dynamics, moving averages, anomalies |

---

## Developer Runbook

### 1. Environment Setup & Server Run
```bash
# Navigate to backend directory
cd backend

# Copy environment configuration template
cp .env.example .env

# Activate virtual environment
source .venv/bin/activate

# Install dependencies if needed
pip install -r requirements.txt

# Start the application server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Database Initialization & Mock Data Ingestion
```bash
# Initialize PostgreSQL schema and tables
python scripts/init_db.py

# Ingest realistic multi-platform mock posts dataset
python scripts/load_mock_data.py
```

### 3. Running the Test Suite
```bash
# Run the complete test suite (561 tests)
PYTHONPATH=. .venv/bin/pytest

# Run tests with verbose output
PYTHONPATH=. .venv/bin/pytest -v

# Run specific Phase 5 test modules
PYTHONPATH=. .venv/bin/pytest tests/test_phase5_api_foundation.py
PYTHONPATH=. .venv/bin/pytest tests/test_phase5_data_timeline_api.py
PYTHONPATH=. .venv/bin/pytest tests/test_phase5_combined_analytics.py
PYTHONPATH=. .venv/bin/pytest tests/test_phase5_openapi.py
```

### 4. Code Hygiene & Git Checks
```bash
# Verify no trailing whitespace or diff issues
git diff --check

# Check repository working tree status
git status
```

---

## Known Limitations & Production Roadmap

1. **Language Scope**: Sentiment and emotion engines are rule-based and optimized primarily for English text; multilingual posts default to neutral if English tokens are missing.
2. **Heuristic Topic Clustering**: Topic extraction relies on statistical keyword and n-gram co-occurrence; deep transformer embeddings (BERT/RoBERTa) are scheduled for future enhancement.
3. **Temporal Trend Windowing**: Trend detection calculates trajectory against the provided historical window; multi-year macroeconomic seasonality is not modeled.
4. **Explicit Demographics Only**: Demographics strictly aggregate explicit, authorized user metadata; the engine intentionally does not infer sensitive traits from raw text to preserve privacy.
5. **CORS Security**: Unrestricted wildcard `*` is not used in production; explicit allowed origins must be configured via `CORS_ORIGINS`.
6. **Authentication Scope**: OAuth2/JWT authentication and per-client API rate limiting are scheduled for post-hackathon enterprise hardening.
