# InsightX — Phase 1: Backend & Database Foundation

## 1. Phase Objective

The objective of Phase 1 was to build the backend and database foundation for InsightX.

Before collecting real social-media data, the system needs a reliable place to store, organize, and retrieve that data.

Phase 1 establishes:

* FastAPI backend
* PostgreSQL database
* Database schema
* Relationships between entities
* SQLAlchemy database connection
* Environment-based configuration
* FastAPI → PostgreSQL integration
* Initial database testing

---

## 2. Technology Stack

### Backend

* Python
* FastAPI
* Uvicorn

### Database

* PostgreSQL 17

### Database ORM / Connection

* SQLAlchemy
* psycopg2

### Configuration

* python-dotenv
* `.env`

### Development

* Git
* GitHub
* Virtual environment (`.venv`)

---

## 3. Project Structure

The relevant structure after Phase 1:

```text
InsightX/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── models/
│   │   ├── services/
│   │   ├── utils/
│   │   ├── config.py
│   │   ├── database.py
│   │   └── main.py
│   │
│   ├── tests/
│   ├── .env
│   ├── .gitignore
│   └── requirements.txt
│
├── frontend/
├── database/
├── ml/
├── data/
├── tests/
├── notebooks/
└── docs/
```

---

# 4. FastAPI Foundation

The FastAPI application is located at:

```text
backend/app/main.py
```

The application currently provides two endpoints.

### Health Check

```text
GET /health
```

Response:

```json
{
    "status": "ok"
}
```

This confirms that the FastAPI application is running.

### Database Health Check

```text
GET /db-health
```

Response:

```json
{
    "database": "insightx"
}
```

This confirms that FastAPI can communicate with PostgreSQL through SQLAlchemy.

---

# 5. PostgreSQL Database

The project uses a PostgreSQL database named:

```text
insightx
```

The database was created locally and PostgreSQL was verified to be accepting connections.

PostgreSQL is used because InsightX needs to store structured, relational, and time-dependent social-media data.

---

# 6. Database Schema

InsightX currently contains eight core tables:

1. `platforms`
2. `users`
3. `posts`
4. `post_metrics`
5. `sentiments`
6. `topics`
7. `post_topics`
8. `collections`

---

## 6.1 Platforms

```text
platforms
```

Stores the social-media platforms from which data is collected.

Important fields:

* `id`
* `name`

Example:

```text
id | name
---+----
1  | X
```

---

## 6.2 Users

```text
users
```

Stores users/accounts belonging to a platform.

Important fields:

* `id`
* `platform_id`
* `username`
* `display_name`
* `followers_count`
* `following_count`
* `created_at`

Relationship:

```text
Platform 1 ────────< Users
```

A platform can have many users.

---

## 6.3 Posts

```text
posts
```

Stores individual social-media posts.

Important fields:

* `id`
* `platform_id`
* `user_id`
* `external_post_id`
* `text`
* `posted_at`
* `collected_at`

Relationships:

```text
Platform 1 ────────< Posts
User     1 ────────< Posts
```

The `external_post_id` identifies the original post on the social-media platform.

---

## 6.4 Post Metrics

```text
post_metrics
```

Stores engagement measurements for posts.

Important fields:

* `post_id`
* `collected_at`
* `likes`
* `comments`
* `shares`
* `views`

Relationship:

```text
Post 1 ────────< Metrics
```

Metrics are stored separately because engagement changes over time.

For example:

```text
10:00 → 120 likes
12:00 → 165 likes
14:00 → 230 likes
```

Instead of overwriting the previous value, InsightX can preserve historical snapshots.

This allows future trend analysis.

---

## 6.5 Sentiments

```text
sentiments
```

Stores sentiment-analysis results for posts.

Important fields:

* `post_id`
* `label`
* `score`
* `model`
* `analyzed_at`

Example:

```text
label = positive
score = 0.94
model = sentiment_model
```

This table will later be populated by the ML/NLP pipeline.

---

## 6.6 Topics

```text
topics
```

Stores topics identified from social-media content.

Important fields:

* `id`
* `name`
* `created_at`

Example topics:

```text
Politics
Sports
Technology
Elections
AI
```

The actual topic extraction will be handled in later phases.

---

## 6.7 Post Topics

```text
post_topics
```

Connects posts with topics.

This table exists because one post can contain multiple topics, and one topic can appear in many posts.

Therefore:

```text
Posts  >────<  Topics
```

This is a many-to-many relationship.

`post_topics` acts as the bridge table.

---

## 6.8 Collections

```text
collections
```

Tracks data-collection sessions.

Important fields:

* `platform_id`
* `started_at`
* `ended_at`
* `status`
* `records_collected`

This will become important when the continuous data-collection system is implemented.

---

# 7. Complete Database Relationship Model

The current foundation can be visualized as:

```text
                 ┌──────────────┐
                 │  Platforms   │
                 └──────┬───────┘
                        │
             ┌──────────┴──────────┐
             ↓                     ↓
       ┌──────────┐          ┌──────────┐
       │  Users   │          │  Posts   │
       └────┬─────┘          └────┬─────┘
            │                     │
            │              ┌──────┼─────────┐
            │              ↓      ↓         ↓
            │         ┌────────┐ ┌──────┐ ┌──────────┐
            │         │Metrics │ │Sent. │ │ Topics   │
            │         └────────┘ └──────┘ └────┬─────┘
            │                                  │
            │                                  │
            │                         ┌────────┴──────┐
            │                         │  Post Topics  │
            │                         └───────────────┘
            │
            └────────────────────────────────────────

                 Platforms
                     │
                     ↓
                Collections
```

---

# 8. Environment Configuration

Database configuration is stored in:

```text
backend/.env
```

Example:

```text
DATABASE_URL=postgresql+psycopg2://USERNAME@localhost:5432/insightx
```

The `.env` file is excluded from Git using `.gitignore`.

This prevents environment-specific configuration and credentials from being committed to the repository.

---

# 9. Configuration Layer

The file:

```text
backend/app/config.py
```

loads the `.env` file and reads the database URL.

Conceptually:

```text
.env
 ↓
python-dotenv
 ↓
config.py
 ↓
DATABASE_URL
```

This keeps configuration separate from application logic.

---

# 10. SQLAlchemy Database Layer

The file:

```text
backend/app/database.py
```

creates the SQLAlchemy engine and session factory.

The architecture is:

```text
DATABASE_URL
      ↓
create_engine()
      ↓
SQLAlchemy Engine
      ↓
SessionLocal
      ↓
get_db()
```

`get_db()` provides a database session to FastAPI endpoints.

The session is closed automatically after the request finishes.

---

# 11. FastAPI Database Dependency

FastAPI uses:

```python
Depends(get_db)
```

to obtain a database session.

The request flow is:

```text
Client
  ↓
FastAPI endpoint
  ↓
Depends(get_db)
  ↓
SQLAlchemy Session
  ↓
PostgreSQL
  ↓
Response
```

The `/db-health` endpoint successfully tested this entire chain.

---

# 12. Database Testing

Initial database testing was performed using realistic sample data.

The following chain was successfully tested:

```text
Platform
   ↓
User
   ↓
Post
   ↓
Post Metrics
```

A test platform was inserted:

```text
X
```

A test user was associated with the platform.

A test post was associated with the user and platform.

Metrics were then associated with the post.

This verified that the primary-key and foreign-key relationships are functioning correctly.

---

# 13. Important Concepts Learned

## Primary Key

A primary key uniquely identifies a record.

Example:

```text
users.id
```

---

## Foreign Key

A foreign key connects one table to another.

Example:

```text
users.platform_id
```

references:

```text
platforms.id
```

---

## One-to-Many Relationship

Example:

```text
Platform 1 → Many Users
```

One platform can contain many users.

---

## Many-to-Many Relationship

Example:

```text
Posts ↔ Topics
```

A post can have multiple topics, and a topic can belong to many posts.

The `post_topics` table manages this relationship.

---

## Time-Series Data

Post metrics are stored with timestamps.

This allows InsightX to preserve historical engagement values instead of only storing the latest value.

This is important for:

* Trend detection
* Engagement growth
* Historical analysis
* Time-based dashboards

---

# 14. Why This Phase Matters

Phase 1 provides the foundation for every later component of InsightX.

Without this foundation:

* Data ingestion would have nowhere reliable to store data.
* ML models would not have structured input.
* APIs could not retrieve analytics results.
* The dashboard would not have a stable data source.
* Historical trend analysis would be difficult.

Therefore:

```text
Phase 1
   ↓
Reliable Data Foundation
   ↓
Phase 2 Data Ingestion
   ↓
Phase 3 ML/NLP
   ↓
Phase 4 Analytics/API
   ↓
Phase 5 Dashboard
   ↓
Phase 6 AI Insights
```

---

# 15. Phase 1 Completion Checklist

* [x] Project architecture
* [x] Backend foundation
* [x] FastAPI application
* [x] PostgreSQL installation
* [x] InsightX database
* [x] Database schema
* [x] Tables and relationships
* [x] SQLAlchemy integration
* [x] Environment configuration
* [x] FastAPI database dependency
* [x] Database connection testing
* [x] Initial database data testing
* [ ] Phase 1 documentation committed

---

# 16. Phase 1 Result

At the end of Phase 1, InsightX has a working backend and relational database foundation.

The system can:

1. Start a FastAPI backend.
2. Connect FastAPI to PostgreSQL.
3. Create database sessions using SQLAlchemy.
4. Store platforms.
5. Store users.
6. Store posts.
7. Store historical post metrics.
8. Store sentiment results.
9. Store topics.
10. Connect posts and topics.
11. Track collection sessions.

The system is now ready to move toward **Phase 2: Data Ingestion Pipeline**.

---

# 17. Next Phase

## Phase 2 — Data Ingestion Pipeline

The next major goal is:

```text
Social Media Platforms
        ↓
Data Collection
        ↓
Raw Data
        ↓
Validation / Cleaning
        ↓
Normalization
        ↓
PostgreSQL
```

Phase 2 will introduce concepts such as:

* APIs
* JSON
* HTTP requests
* Data ingestion
* Data validation
* Data cleaning
* ETL/ELT concepts
* Platform-specific data
* Continuous collection
* Duplicate handling
* Historical storage

This will be the first phase where InsightX starts behaving like a real social-media analytics system rather than just a backend/database foundation.
