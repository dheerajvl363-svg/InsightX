# InsightX — Phase 3: Social Media Analytics Platform

## 1. Phase Overview & SIH PS 26152 Objective

Phase 3 implements the comprehensive **Analytics Platform** for **InsightX**, addressing **Smart India Hackathon 2026 Problem Statement 26152 (Social Media Analytics)**.

The objective of Phase 3 is to turn multi-platform social media streams into structured, actionable public intelligence by extracting:
- **Data Quality & Entity Sanitization**: Noise removal, zero-width stripping, and quality assurance.
- **Sentiment Polarity**: Positive, neutral, and negative classification with polarity scoring.
- **Emotion Recognition**: 7-class Ekman emotion profiling (`joy`, `sadness`, `anger`, `fear`, `surprise`, `disgust`, `neutral`).
- **Topic & Narrative Clustering**: Unsupervised n-gram and keyword clustering.
- **Temporal Trend & Narrative Velocity**: Detection of emerging narratives, volume spikes, and growth rates.
- **Demographic Intelligence**: Privacy-preserving aggregation of age, gender, and geographic distributions.
- **Unified Analytics REST API**: In-memory multi-layer analytics orchestration.

---

## 2. Completed Phase 3 Architecture

The analytics platform operates as a deterministic, modular pipeline:

```text
Raw Platform Data (X, Reddit, Telegram, YouTube)
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

## 3. Directory Structure

```text
backend/
├── app/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── analytics.py      # REST endpoints (Phase 3.7 & Unified API)
│   │   │   ├── ingestion.py      # Phase 2 Ingestion endpoints
│   │   │   └── __init__.py
│   ├── models/                   # SQLAlchemy DB ORM models
│   ├── schemas/
│   │   ├── analytics_api.py      # CombinedAnalyzeRequest, CombinedAnalyticsResponse
│   │   ├── analytics.py          # PostSummary, Aggregation models
│   │   ├── data_quality.py       # AnalyticsReadyPost, BatchDataQualityResult
│   │   ├── demographic.py        # DemographicDistribution, BatchDemographicResult
│   │   ├── emotion.py            # EmotionResult, BatchEmotionResult
│   │   ├── platform.py           # Platform schemas
│   │   ├── post.py               # RawPostPayload, NormalizedPost
│   │   ├── sentiment.py          # SentimentResult, BatchSentimentResult
│   │   ├── topic.py              # ExtractedTopic, BatchTopicResult
│   │   └── trend.py              # TopicTrendResult, BatchTrendResult
│   ├── services/
│   │   ├── adapters/             # Platform adapters (X, Reddit, Telegram, YouTube)
│   │   ├── data_quality.py       # Phase 3.1 Data Quality Service
│   │   ├── demographic/          # Phase 3.6 Demographic Intelligence Engine & Service
│   │   ├── emotion/              # Phase 3.3 Emotion Analysis Engine & Service
│   │   ├── normalizer.py         # Phase 2 Data Normalizer
│   │   ├── sentiment/            # Phase 3.2 Sentiment Analysis Engine & Service
│   │   ├── topic/                # Phase 3.4 Topic Extraction Engine & Service
│   │   └── trend/                # Phase 3.5 Trend Detection Engine & Service
│   ├── database.py               # DB Session & engine configuration
│   └── main.py                   # FastAPI Application initialization
└── tests/
    ├── test_integration.py       # Phase 3.8.2 End-to-end integration tests
    ├── test_reliability.py       # Phase 3.8.3 Robustness, isolation & performance tests
    └── test_*.py                 # Unit & regression test suites (297 tests total)
```

---

## 4. Phase 3 Components Detail

### 3.1 Data Quality & Analytics Input Layer
- **Service**: `DataQualityService` (`app/services/data_quality.py`)
- **Key Schema**: `AnalyticsReadyPost` (`app/schemas/data_quality.py`)
- Sanitizes incoming text, strips unprintable/zero-width characters (`\u200b`, `\ufeff`), standardizes line breaks, and preserves hashtags, emojis, and mentions.
- Validates temporal sanity (flags future timestamps > 24h and pre-2000 dates).
- Segregates rejected items into `RejectedRecord` without contaminating valid batches.

### 3.2 Sentiment Analysis Engine
- **Service**: `SentimentAnalysisService` (`app/services/sentiment/service.py`)
- **Key Schema**: `BatchSentimentResult`, `SentimentResult` (`app/schemas/sentiment.py`)
- Calculates continuous polarity scores (`[-1.0, 1.0]`) and confidence metrics.
- Classifies posts into `positive`, `neutral`, and `negative`, handling negation and emphasis punctuation.

### 3.3 Emotion Analysis Engine
- **Service**: `EmotionAnalysisService` (`app/services/emotion/service.py`)
- **Key Schema**: `BatchEmotionResult`, `EmotionResult` (`app/schemas/emotion.py`)
- Detects 7 discrete emotional states: `joy`, `sadness`, `anger`, `fear`, `surprise`, `disgust`, and `neutral`.
- Computes complete normalized probability distributions across all 7 emotions.

### 3.4 Topic Extraction & Narrative Detection
- **Service**: `TopicAnalysisService` (`app/services/topic/service.py`)
- **Key Schema**: `BatchTopicResult`, `ExtractedTopic` (`app/schemas/topic.py`)
- Unsupervised n-gram extraction and co-occurrence clustering.
- Generates human-readable topic labels, keywords, and preserves associated post identifiers.

### 3.5 Trend Detection & Emerging Narrative Analysis
- **Service**: `TrendAnalysisService` (`app/services/trend/service.py`)
- **Key Schema**: `BatchTrendResult`, `TopicTrendResult` (`app/schemas/trend.py`)
- Compares activity across sliding windows (current vs. baseline).
- Classifies trends into `EMERGING`, `SPIKING`, `GROWING`, `STABLE`, and `DECLINING` based on percentage growth and statistical z-scores.

### 3.6 Demographic Intelligence
- **Service**: `DemographicAnalysisService` (`app/services/demographic/service.py`)
- **Key Schema**: `BatchDemographicResult`, `DemographicDistribution` (`app/schemas/demographic.py`)
- Aggregates reported/inferred user demographic metadata (Age Group, Gender, Location).
- Applies k-anonymity privacy suppression (`min_group_size`) to prevent individual identification.
- Cross-correlates demographics with topics, sentiment classes, and trending narratives.

### 3.7 Analytics REST API
- **Router**: `app/api/routes/analytics.py`
- **Key Schema**: `CombinedAnalyzeRequest`, `CombinedAnalyticsResponse` (`app/schemas/analytics_api.py`)
- Exposes dedicated endpoints per engine and a unified multi-layer pipeline endpoint.

---

## 5. API Reference

### Health Check Endpoints
- `GET /health` — Service health probe (`{"status": "ok"}`).
- `GET /db-health` — PostgreSQL database connectivity verification.

### Individual Analytics Endpoints
- `POST /api/v1/analytics/sentiment` — Batch or text sentiment analysis.
- `POST /api/v1/analytics/emotion` — 7-class discrete emotion detection.
- `POST /api/v1/analytics/topics` — Unsupervised topic clustering.
- `POST /api/v1/analytics/trends` — Temporal velocity and surge classification.
- `POST /api/v1/analytics/demographics` — Demographic distribution and cross-breakdowns.

### Unified Orchestration Endpoint
- `POST /api/v1/analytics/analyze` — Executes all requested analytics layers in a single request.

#### Request Schema: `CombinedAnalyzeRequest`
- `raw_posts`: List of `RawPostPayload` (or dictionaries).
- `posts`: Optional list of pre-validated `AnalyticsReadyPost`.
- `reference_time`: Upper-bound evaluation timestamp in UTC (ISO 8601).
- `window_duration_seconds`: Sliding window duration (default 3600 seconds).
- `include_sentiment`: Boolean (default `true`).
- `include_emotion`: Boolean (default `true`).
- `include_topics`: Boolean (default `true`).
- `include_trends`: Boolean (default `true`).
- `include_demographics`: Boolean (default `true`).

#### Example Request: `POST /api/v1/analytics/analyze`
```json
{
  "raw_posts": [
    {
      "platform": "X",
      "external_id": "hyd_metro_001",
      "text": "Hyderabad metro rail fares increased drastically today! Completely outrageous! #MetroFares",
      "author_username": "angry_commuter",
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

## 6. Developer Runbook

### Environment Activation & Server Run
```bash
# Navigate to backend
cd backend

# Activate virtual environment
source .venv/bin/activate

# Run FastAPI application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Running Test Suites
```bash
# Run complete test suite (297 tests)
.venv/bin/python -m unittest discover -s tests -p "test_*.py"

# Run Phase 3 End-to-End Integration tests
.venv/bin/python -m unittest tests/test_integration.py

# Run Phase 3 Reliability & Quality tests
.venv/bin/python -m unittest tests/test_reliability.py
```

### Git Quality & Formatting Checks
```bash
# Verify no trailing whitespace or git errors
git diff --check

# Check repository working tree status
git status
```

---

## 7. Current Limitations & Assumptions

1. **Language Scope**: Rule-based sentiment and emotion engines are primarily English-focused. Multilingual posts default to neutral unless English sentiment tokens are detected.
2. **Deterministic Heuristic Topics**: Topic detection uses statistical n-gram and keyword co-occurrence heuristics; deep transformer-based semantic embeddings (e.g., BERT/RoBERTa) are not yet integrated.
3. **Temporal Sliding Windows**: Trend detection depends strictly on the window duration and the historical batch provided; macroeconomic multi-year seasonality is not modeled.
4. **Explicit Demographics Only**: Demographics strictly aggregate explicit, authorized user metadata; the platform intentionally refuses to infer sensitive protected traits from raw post text.
5. **Public Stream Unknown Coverage**: In unstructured public feeds without profile metadata, unknown demographic coverage will naturally be high.
6. **In-Memory Pipeline Execution**: The `/api/v1/analytics/analyze` endpoint computes multi-layer analytics in-memory for the incoming batch; long-term analytics warehousing is handled asynchronously.
7. **Security Scope**: OAuth2 authentication and API rate-limiting middleware are scheduled for subsequent infrastructure phases.
