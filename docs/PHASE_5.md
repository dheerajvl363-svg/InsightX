# InsightX — Phase 5: REST API, OpenAPI Documentation & Release Readiness

## 1. Phase Overview & SIH PS 26152 Objective

Phase 5 delivers the production-grade **FastAPI REST API Layer** for **InsightX**, transforming the ingestion pipeline (Phase 2), atomic NLP extractors (Phase 3), and multi-dimensional analytical engines (Phase 4) into an accessible, typed, documented, and resilient web service for **Smart India Hackathon 2026 Problem Statement 26152 (Social Media Analytics)**.

Phase 5 establishes a reliable communication bridge for the frontend application (Phase 6), intelligence analysts, external integrations, and hackathon evaluation judges.

---

## 2. Phase 5 Subsystem Milestones (Phases 5.1 – 5.9)

| Milestone | Key Objective | Core Deliverables |
|---|---|---|
| **Phase 5.1** | **API Foundation** | FastAPI application setup, async lifespan context, application metadata (`InsightX Social Media Analytics API`), configuration loader, health endpoints (`/health`, `/db-health`, `/api/v1/health`), and modular router mounting. |
| **Phase 5.2** | **Schemas & Validation** | Strict Pydantic v2 domain schemas (`app/schemas/`), field constraints, type bounds, and serialization contracts for all request and response models. |
| **Phase 5.3** | **Analytics REST Endpoints & Network Graph** | Dedicated endpoints for platform distributions, engagement metrics, time-series bucketing, author leaderboards, topics, sentiment, emotion, trend momentum, demographics, and co-occurrence hashtag/mention network analysis. |
| **Phase 5.4** | **Data, Posts & Timeline API** | Filtered and paginated post querying (`/api/v1/posts`), post lookup by ID (`/api/v1/posts/{post_id}`), platform discovery (`/api/v1/platforms`), and chronological timeline volume aggregation (`/api/v1/timeline`). |
| **Phase 5.5** | **Combined Analytics & Dashboard API** | Multi-signal aggregation endpoint (`/api/v1/analytics/overview`) bundling total post counts, platform distributions, sentiment overview, top trending topics, viral posts, and timeline trends into a single call for dashboard widgets. |
| **Phase 5.6** | **Standardized Error Handling** | Global exception handlers (`setup_exception_handlers`) intercepting `RequestValidationError`, `InsightXException`, `SQLAlchemyError`, and uncaught exceptions to return a standardized `ErrorResponse` schema without exposing stack traces or database queries. |
| **Phase 5.7** | **API Testing & Hardening** | Comprehensive endpoint test suites covering pagination boundaries, query parameter validation, invalid IDs, malformed bodies, empty filters, and edge cases (543 passing tests). |
| **Phase 5.8** | **OpenAPI & API Documentation** | Rich OpenAPI 3.1.0 metadata, tag taxonomies, route summaries, detailed docstrings, request/response examples, and interactive Swagger UI (`/docs`) and ReDoc (`/redoc`) documentation. |
| **Phase 5.9** | **Release Readiness & Phase 6 Hand-off** | Configurable CORS middleware, `.env.example` template, zero-leak production defaults, live startup verification, and documentation synchronization. |

---

## 3. End-to-End API Architecture

```text
Browser / Frontend Client (Phase 6: Next.js / Vite / Vue)
                           │
                           ▼  [HTTP / JSON]
           ┌───────────────────────────────┐
           │      CORSMiddleware           │  <-- Configurable allowed origins
           └──────────────┬────────────────┘
                          ▼
           ┌───────────────────────────────┐
           │  Global Exception Handlers    │  <-- 400, 404, 422, 500 standardized responses
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

## 4. API Route Catalog

The API exposes **35 distinct route paths** with **41 operation endpoints**:

### 4.1 System & Health (`tags=["Health"]`)
- `GET /health`: Root legacy health probe returning `{"status": "ok"}` for container orchestrators and load balancers.
- `GET /db-health`: Verifies active database connection and returns active database name.
- `GET /api/v1/health`: Detailed Phase 5 health status including version, environment (`APP_ENV`), and database connectivity status.

### 4.2 Posts & Content Discovery (`tags=["Posts"]`)
- `GET /api/v1/posts`: Paginated list of posts with filtering by `platform`, `sentiment`, `keyword`, `author`, date ranges (`start_date`, `end_date`), and metric thresholds (`min_likes`, `min_comments`, `min_shares`, `min_views`). Returns `PostListResponse`.
- `GET /api/v1/posts/{post_id}`: Detailed single post retrieval by integer ID, including full metadata, raw payload preview, and engagement metrics. Returns 404 on missing post.

### 4.3 Platform Discovery (`tags=["Platforms"]`)
- `GET /api/v1/platforms`: List of all supported social platforms (`X`, `Reddit`, `Telegram`, `YouTube`) with metadata, active post counts, and capabilities. Returns `PlatformListResponse`.

### 4.4 Timeline Analytics (`tags=["Timeline"]`)
- `GET /api/v1/timeline`: Chronological time-series post volume aggregated into discrete temporal intervals (`hour`, `day`, `week`) with per-platform breakdown. Returns `TimelineResponse`.

### 4.5 High-Level Analytics (`tags=["Analytics"]`)
- `GET /api/v1/analytics/overview`: High-level multi-signal dashboard summary bundling total posts, platform shares, sentiment breakdown, top topics, active trends, and recent viral outliers into a single unified response.
- `GET /api/v1/analytics/posts`: Paginated posts matching analytical filters.
- `GET /api/v1/analytics/count`: Fast count of posts matching applied criteria.
- `GET /api/v1/analytics/platforms`: Total post volume and engagement distributions by platform.
- `GET /api/v1/analytics/platforms/compare`: Cross-platform comparative benchmark across metrics and sentiment.
- `GET /api/v1/analytics/languages`: Distribution of detected post languages.
- `GET /api/v1/analytics/engagement`: Aggregated engagement metrics (total/average likes, comments, shares, views, engagement rate).
- `GET /api/v1/analytics/timeseries`: Time-series post volume distributions.
- `GET /api/v1/analytics/timeseries/engagement`: Time-series engagement momentum tracking.
- `GET /api/v1/analytics/authors`: Most active and highest-impact social media authors.
- `GET /api/v1/analytics/topics` & `POST /api/v1/analytics/topics`: Top extracted keyword clusters and thematic topics.
- `GET /api/v1/analytics/sentiment` & `POST /api/v1/analytics/sentiment`: Sentiment distribution (`positive`, `neutral`, `negative`) and Net Sentiment Score ($\text{NSS}$).
- `POST /api/v1/analytics/emotion`: Emotion classifications based on Ekman's 7-class taxonomy (`joy`, `sadness`, `anger`, `fear`, `surprise`, `disgust`, `neutral`).
- `GET /api/v1/analytics/trends` & `POST /api/v1/analytics/trends`: Trending topics with velocity, acceleration, and spike detection.
- `POST /api/v1/analytics/demographics`: Privacy-preserving demographic aggregations with k-anonymity suppression.
- `GET /api/v1/analytics/network` & `POST /api/v1/analytics/network`: Graph structure of co-occurring hashtags and user mentions (nodes and edges with weights for graph visualizers).
- `POST /api/v1/analytics/analyze`: Orchestrated pipeline executing sentiment, emotion, topics, and demographic analysis in one call.

### 4.6 Ingestion Pipeline (`tags=["Ingestion"]`)
- `POST /api/v1/ingestion/posts`: Ingest a single raw social media post.
- `POST /api/v1/ingestion/posts/batch`: Ingest multiple raw posts with duplicate detection.
- `GET /api/v1/ingestion/platforms`: Ingestion adapter capabilities.

### 4.7 Low-Level Analytics Engine (`tags=["Analytics Engine"]`)
- `GET /api/v1/analytics/engine/health`: Engine health status.
- `GET /api/v1/analytics/engine/capabilities`: Supported algorithmic capabilities.
- `POST /api/v1/analytics/engine/analyze`: Full Phase 4 engine pipeline execution.
- `POST /api/v1/analytics/engine/engagement`: Phase 4.2 Engagement & Virality engine.
- `POST /api/v1/analytics/engine/sentiment`: Phase 4.3 Sentiment & NSS engine.
- `POST /api/v1/analytics/engine/trends`: Phase 4.4 Trend & Momentum engine.
- `POST /api/v1/analytics/engine/narratives`: Phase 4.5 Narrative Dynamics engine.
- `POST /api/v1/analytics/engine/time-series`: Phase 4.6 Time-Series Dynamics engine.

---

## 5. Domain Schemas & Validation Models

All data models utilize strict Pydantic v2 schemas:

### Standard Paginated Post Model (`PostListResponse`)
```json
{
  "total": 1,
  "limit": 50,
  "offset": 0,
  "items": [
    {
      "id": 1,
      "platform": "X",
      "external_post_id": "ext_101",
      "text": "Artificial Intelligence in health and technology. #AI #Tech",
      "author_username": "tech_lead",
      "author_display_name": "Tech Lead",
      "posted_at": "2026-09-08T12:00:00Z",
      "collected_at": "2026-09-08T12:00:00Z",
      "url": "https://x.com/tech_lead/status/101",
      "language": "en",
      "metrics": {
        "likes": 150,
        "comments": 25,
        "shares": 30,
        "views": 1200
      },
      "metadata": {}
    }
  ]
}
```

### Unified Dashboard Model (`OverviewResponse`)
```json
{
  "total_posts": 10500,
  "platform_distribution": {
    "X": 4200,
    "Reddit": 3100,
    "Telegram": 1800,
    "YouTube": 1400
  },
  "sentiment_summary": {
    "positive": 5500,
    "neutral": 3200,
    "negative": 1800,
    "net_sentiment_score": 0.352
  },
  "top_topics": [
    {"topic": "AI Safety", "count": 1240, "sentiment": "positive"},
    {"topic": "Green Energy", "count": 890, "sentiment": "neutral"}
  ],
  "top_trends": [
    {"term": "#Innovation", "growth_rate": 142.5, "velocity": 85.0}
  ],
  "timeline": [
    {"bucket": "2026-09-08T00:00:00Z", "count": 420}
  ]
}
```

---

## 6. Standardized Error Handling Architecture

In accordance with Phase 5.6, all API errors conform to the standard `ErrorResponse` schema:

```json
{
  "detail": "Descriptive error message",
  "error_code": "RESOURCE_NOT_FOUND",
  "status_code": 404,
  "errors": [
    {
      "field": "post_id",
      "message": "Post with ID 99999 was not found",
      "type": "not_found"
    }
  ]
}
```

### Security & Sanitization Rules
1. **No Stack Traces**: Internal Python stack traces and tracebacks are never returned to clients.
2. **No SQL Query Leakage**: `SQLAlchemyError` exceptions are caught, logged internally to server logs, and masked into a safe `500 Internal Server Error` with `error_code: "DATABASE_ERROR"`.
3. **Pydantic Validation**: Request validation failures automatically generate clear 422 errors mapping each invalid field without exposing internal server paths.

---

## 7. Security, CORS & Environment Configuration

### CORS Configuration
FastAPI `CORSMiddleware` is configured in `backend/app/main.py`:
- **Development**: When `APP_ENV != "production"`, default allowed origins include standard local frontend dev ports:
  - `http://localhost:3000`, `http://127.0.0.1:3000` (Next.js / CRA)
  - `http://localhost:5173`, `http://127.0.0.1:5173` (Vite)
  - `http://localhost:8080`, `http://127.0.0.1:8080` (Vue)
- **Production**: When `APP_ENV == "production"`, CORS defaults to strict (`[]`), requiring explicit configuration via the `CORS_ORIGINS` environment variable. Unrestricted wildcard `*` is **not** used as default.
- **Allowed Methods**: All HTTP methods (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `OPTIONS`).
- **Credentials**: `allow_credentials=True` enabled for cookie/token compatibility with explicit origins.

### Environment Template (`backend/.env.example`)
```env
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/insightx
APP_ENV=development
APP_VERSION=5.1.0
DEBUG=false
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173
```

---

## 8. Test Coverage & Verification

### Test Suite Execution
```bash
cd backend
PYTHONPATH=. .venv/bin/pytest
```
- **Total Tests**: **561 passed**
- **Test Modules**: 27 test files
- **Execution Time**: ~4.1 seconds
- **Pass Rate**: 100% (0 failures, 0 errors)

### Phase 5 Test Modules
| Test File | Description | Count |
|---|---|---|
| `test_phase5_api_foundation.py` | Health endpoints, app metadata, CORS headers, preflights, config | 33 tests |
| `test_phase5_schemas.py` | Schema serialization, validation constraints, default values | 82 tests |
| `test_phase5_analytics_endpoints.py` | Engagement, timeseries, platforms, authors endpoints | 9 tests |
| `test_phase5_data_timeline_api.py` | Posts filtering, single post lookup, platforms, timeline | 13 tests |
| `test_phase5_combined_analytics.py` | Overview dashboard endpoint and cross-signal synthesis | 6 tests |
| `test_phase5_error_handling.py` | 400, 404, 422, 500 error handlers and sanitization | 5 tests |
| `test_phase5_api_hardening.py` | Edge cases, boundary inputs, pagination limits, query params | 12 tests |
| `test_phase5_openapi.py` | OpenAPI 3.1.0 schema structure, tag metadata, schema examples | 10 tests |

---

## 9. Frontend Integration Expectations (Phase 6 Hand-off)

The frontend application (Phase 6) should consume the backend according to the following conventions:

1. **Base URL**: `http://localhost:8000/api/v1`
2. **Dashboard Overview View**:
   - Primary endpoint: `GET /api/v1/analytics/overview`
   - Populates KPI summary cards, platform pie chart, sentiment gauge, top topics table, and timeline trend graph in one query.
3. **Posts Explorer View**:
   - Primary endpoint: `GET /api/v1/posts?platform=X&sentiment=positive&limit=50&offset=0`
   - Individual post modal: `GET /api/v1/posts/{post_id}`
4. **Timeline & Volume View**:
   - Primary endpoint: `GET /api/v1/timeline?interval=day`
5. **Network Graph View**:
   - Primary endpoint: `GET /api/v1/analytics/network`
   - Renders node-edge co-occurrence graphs for hashtags and mentions.
6. **Error Response Parsing**:
   - Inspect `response.data.detail` or `response.data.errors` array for structured validation messages.
