import asyncio
from datetime import datetime
import json
import unittest

from app.database import SessionLocal
from app.main import app
from app.models.metric import PostMetric
from app.models.post import Post


def call_api(method: str, path: str, body: dict = None) -> tuple[int, dict]:
    """
    Executes a native ASGI HTTP request against the FastAPI application.
    Tests full FastAPI pipeline: routing, dependency injection, validation, and serialization.
    """
    body_bytes = json.dumps(body).encode("utf-8") if body is not None else b""
    response_headers = {}
    response_body = []
    status_code = None

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method.upper(),
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body_bytes)).encode()),
        ],
    }

    async def receive():
        return {"type": "http.request", "body": body_bytes, "more_body": False}

    async def send(message):
        nonlocal status_code
        if message["type"] == "http.response.start":
            status_code = message["status"]
            for k, v in message.get("headers", []):
                response_headers[k.decode()] = v.decode()
        elif message["type"] == "http.response.body":
            response_body.append(message.get("body", b""))

    async def run():
        await app(scope, receive, send)

    asyncio.run(run())

    raw_text = b"".join(response_body).decode("utf-8")
    try:
        data = json.loads(raw_text)
    except Exception:
        data = {"raw_text": raw_text}

    return status_code, data


class TestIngestionAPI(unittest.TestCase):
    """
    Integration tests for Ingestion API routes mounted at /api/v1/ingestion.
    """

    TEST_PREFIX = "test_api_post_"

    def setUp(self):
        self.created_post_ids = []
        self.db = SessionLocal()

    def tearDown(self):
        # Clean up posts created during tests
        if self.created_post_ids:
            self.db.query(PostMetric).filter(PostMetric.post_id.in_(self.created_post_ids)).delete(
                synchronize_session=False
            )
            self.db.query(Post).filter(Post.id.in_(self.created_post_ids)).delete(
                synchronize_session=False
            )
            self.db.commit()
        self.db.close()

    def test_1_create_single_post(self):
        ext_id = f"{self.TEST_PREFIX}001"
        payload = {
            "platform": "twitter",
            "external_id": ext_id,
            "text": "Hello world from InsightX API!",
            "author_username": "@insightx_dev",
            "author_display_name": "InsightX Dev",
            "posted_at": "2026-09-08T01:00:00Z",
            "url": "https://x.com/insightx/status/1",
            "language": "EN",
            "metrics": {"likes": 50, "comments": 5, "shares": 10, "views": 500},
            "metadata": {"sentiment_ready": True},
        }

        status_code, data = call_api("POST", "/api/v1/ingestion/posts", payload)
        self.assertEqual(status_code, 201)
        self.assertEqual(data["status"], "success")
        self.assertFalse(data["is_duplicate"])
        self.assertEqual(data["platform"], "X")
        self.assertEqual(data["external_post_id"], ext_id)
        self.assertIsNotNone(data["post_id"])
        self.created_post_ids.append(data["post_id"])

    def test_2_duplicate_post_handled_safely(self):
        ext_id = f"{self.TEST_PREFIX}002"
        payload = {
            "platform": "telegram",
            "external_id": ext_id,
            "text": "Telegram broadcast channel message",
            "username": "insightx_channel",
        }

        # 1st call: Created (201)
        code1, data1 = call_api("POST", "/api/v1/ingestion/posts", payload)
        self.assertEqual(code1, 201)
        self.assertFalse(data1["is_duplicate"])
        post_id = data1["post_id"]
        self.created_post_ids.append(post_id)

        # 2nd call: Duplicate (200 OK)
        code2, data2 = call_api("POST", "/api/v1/ingestion/posts", payload)
        self.assertEqual(code2, 200)
        self.assertTrue(data2["is_duplicate"])
        self.assertEqual(data2["status"], "duplicate_ignored")
        self.assertEqual(data2["post_id"], post_id)

        # Ensure only 1 record exists in DB
        count = self.db.query(Post).filter_by(id=post_id).count()
        self.assertEqual(count, 1)

    def test_3_batch_ingestion_accepts_multiple_posts(self):
        ext1 = f"{self.TEST_PREFIX}batch_1"
        ext2 = f"{self.TEST_PREFIX}batch_2"

        batch_payload = [
            {
                "platform": "reddit",
                "external_id": ext1,
                "text": "Reddit submission on r/dataanalytics",
                "username": "reddit_user_1",
            },
            {
                "platform": "youtube",
                "external_id": ext2,
                "text": "InsightX walkthrough video",
                "metrics": {"likes": 1200, "views": 45000},
            },
        ]

        status_code, data = call_api("POST", "/api/v1/ingestion/posts/batch", batch_payload)
        self.assertEqual(status_code, 200)
        self.assertEqual(data["total_received"], 2)
        self.assertEqual(data["successful"], 2)
        self.assertEqual(data["duplicates"], 0)
        self.assertEqual(data["failed"], 0)
        self.assertEqual(len(data["results"]), 2)

        for r in data["results"]:
            if r.get("post_id"):
                self.created_post_ids.append(r["post_id"])

    def test_4_batch_response_counts_duplicates_and_failures(self):
        ext_existing = f"{self.TEST_PREFIX}batch_existing"
        # Pre-seed ext_existing
        pre_code, pre_data = call_api(
            "POST",
            "/api/v1/ingestion/posts",
            {"platform": "X", "external_id": ext_existing, "text": "Pre-existing"},
        )
        self.created_post_ids.append(pre_data["post_id"])

        ext_new = f"{self.TEST_PREFIX}batch_new"
        ext_dup = ext_existing

        # Submit batch with: 1 new, 1 duplicate, 1 invalid (blank platform)
        batch_payload = [
            {"platform": "X", "external_id": ext_new, "text": "Fresh post"},
            {"platform": "X", "external_id": ext_dup, "text": "Duplicate submission"},
            {"platform": "   ", "external_id": "invalid_post"},
        ]

        status_code, data = call_api("POST", "/api/v1/ingestion/posts/batch", batch_payload)
        self.assertEqual(status_code, 200)
        self.assertEqual(data["total_received"], 3)
        self.assertEqual(data["successful"], 1)
        self.assertEqual(data["duplicates"], 1)
        self.assertEqual(data["failed"], 1)

        for r in data["results"]:
            if r.get("post_id") and r["post_id"] not in self.created_post_ids:
                self.created_post_ids.append(r["post_id"])

    def test_5_get_platforms(self):
        status_code, data = call_api("GET", "/api/v1/ingestion/platforms")
        self.assertEqual(status_code, 200)
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 4)

        platform_names = [p["name"] for p in data]
        self.assertIn("X", platform_names)
        self.assertIn("Telegram", platform_names)
        self.assertIn("Reddit", platform_names)
        self.assertIn("YouTube", platform_names)

    def test_6_invalid_payload_rejected(self):
        # Missing platform and external_id
        invalid_payload = {"text": "Missing all identifiers"}
        status_code, data = call_api("POST", "/api/v1/ingestion/posts", invalid_payload)
        self.assertEqual(status_code, 422)  # FastAPI Unprocessable Entity

    def test_7_existing_health_check(self):
        status_code, data = call_api("GET", "/health")
        self.assertEqual(status_code, 200)
        self.assertEqual(data, {"status": "ok"})

    def test_8_existing_db_health_check(self):
        status_code, data = call_api("GET", "/db-health")
        self.assertEqual(status_code, 200)
        self.assertEqual(data, {"database": "insightx"})

    def test_9_database_records_queryable_after_api_call(self):
        ext_id = f"{self.TEST_PREFIX}verify_db"
        payload = {
            "platform": "telegram",
            "external_id": ext_id,
            "text": "Verifying database queryability after HTTP ingestion",
            "language": "EN",
            "url": "https://t.me/insightx/100",
            "metrics": {"views": 1500},
        }

        status_code, data = call_api("POST", "/api/v1/ingestion/posts", payload)
        self.assertEqual(status_code, 201)
        post_id = data["post_id"]
        self.created_post_ids.append(post_id)

        # Directly query SQLAlchemy model
        post = self.db.query(Post).filter_by(id=post_id).first()
        self.assertIsNotNone(post)
        self.assertEqual(post.external_post_id, ext_id)
        self.assertEqual(post.platform.name, "Telegram")
        self.assertEqual(post.url, "https://t.me/insightx/100")
        self.assertEqual(post.language, "en")
        self.assertEqual(len(post.metrics), 1)
        self.assertEqual(post.metrics[0].views, 1500)


if __name__ == "__main__":
    unittest.main()
