# InsightX — Mock Social Media Dataset

This directory contains realistic sample social media data used to test, demonstrate, and benchmark the InsightX Phase 2 ingestion and storage pipeline.

---

## Overview

- **File**: `mock_posts.json`
- **Total Records**: 47
- **Platforms Represented**:
  - **X (Twitter)**: Public tweets, threads, tech and civic discussions.
  - **Telegram**: Channel broadcasts, news digests, civic alerts.
  - **Reddit**: Forum discussions, Q&A, tech benchmarks, reviews.
  - **YouTube**: Video metadata, educational tutorials, tech analysis.

---

## Languages Represented

- **English (`en`)**: Primary tech, research, and civic discussions.
- **Telugu (`te`)**: Regional infrastructure, science, and news updates.
- **Hindi (`hi`)**: Space research, technology, and weather announcements.
- **Mixed / Regional Dialects**: Hinglish and Tenglish informal consumer and civic posts.

---

## Edge Cases & Pipeline Demonstrations

1. **Schema Aliases**: Demonstrates normalization of raw keys (`content`, `message`, `caption` → `text`; `id`, `post_id` → `external_id`; `author`, `username` → `author_username`).
2. **Missing Optional Fields**: Tests graceful handling of posts lacking URLs, author profiles (anonymous broadcast channels), or engagement metrics.
3. **Timezone Variety**: Covers UTC (`Z`), positive offsets (`+05:30` IST), and negative offsets (`-04:00` EDT), testing automatic conversion to UTC `datetime`.
4. **Deliberate Duplicates**: Includes 4 identical platform/external-ID records with updated engagement metrics to demonstrate safe deduplication and time-series snapshotting without duplicate post insertion.
5. **Handle Cleaning**: Automatically trims and strips leading `@` symbols from usernames.

---

## How to Load the Dataset

Run the automated loader script from the repository root:

```bash
backend/.venv/bin/python backend/scripts/load_mock_data.py
```

The loader is completely idempotent: running it multiple times safely updates metric snapshots without creating duplicate post records.
