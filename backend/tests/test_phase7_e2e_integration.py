import asyncio
from datetime import datetime, timedelta, timezone
import json
import unittest

from app.database import SessionLocal
from app.main import app
from app.models.post import Post
from app.models.user import User
from app.schemas.post import RawPostPayload
from app.services.ingestion import IngestionService
from app.services.normalizer import DataNormalizer


def call_api(method: str, path: str, body: dict = None) -> tuple[int, dict]:
    """Helper to simulate ASGI HTTP calls against FastAPI without starting a live server."""
    if "?" in path:
        clean_path, query_str = path.split("?", 1)
    else:
        clean_path, query_str = path, ""

    body_bytes = json.dumps(body).encode("utf-8") if body is not None else b""
    response_headers = {}
    response_body = []
    status_code = None

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method.upper(),
        "path": clean_path,
        "raw_path": clean_path.encode(),
        "query_string": query_str.encode(),
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


class TestPhase7EndToEndSystemIntegration(unittest.TestCase):
    """
    Phase 7.1 Comprehensive End-to-End System Validation Suite.
    Validates complete data flow: Ingestion -> Database -> FastAPI -> Frontend API Contracts.
    """

    @classmethod
    def setUpClass(cls):
        """Seed representative multi-platform data to validate end-to-end analytical pipeline."""
        cls.db = SessionLocal()
        cls.normalizer = DataNormalizer()
        cls.ingestion_service = IngestionService(cls.db)

        now = datetime.now(timezone.utc)
        cls.seed_posts = [
            # X (Twitter) Posts
            RawPostPayload(
                platform="X",
                external_id="p7_e2e_x_1",
                text="Artificial intelligence and real-time social analytics are transforming cybersecurity #AI #Intel",
                author_username="sec_researcher",
                author_display_name="Cyber Intelligence Researcher",
                posted_at=now - timedelta(hours=3),
                language="en",
                url="https://x.com/sec_researcher/status/p7_e2e_x_1",
                metrics={"likes": 420, "comments": 85, "shares": 140, "views": 12500},
            ),
            RawPostPayload(
                platform="X",
                external_id="p7_e2e_x_2",
                text="Emerging threat intelligence indicators detected in coordinated social disinformation #Intel #Cyber",
                author_username="threat_analyst",
                author_display_name="Threat Intel Analyst",
                posted_at=now - timedelta(hours=2),
                language="en",
                url="https://x.com/threat_analyst/status/p7_e2e_x_2",
                metrics={"likes": 210, "comments": 42, "shares": 65, "views": 8200},
            ),
            # Reddit Post
            RawPostPayload(
                platform="Reddit",
                external_id="p7_e2e_rd_1",
                text="Comprehensive review of open-source network graph analytics for social media monitoring #OSINT",
                author_username="osint_guru",
                author_display_name="u/osint_guru",
                posted_at=now - timedelta(hours=5),
                language="en",
                url="https://reddit.com/r/osint/comments/p7_e2e_rd_1",
                metrics={"likes": 180, "comments": 95, "shares": 30, "views": 5400},
            ),
            # Telegram Post
            RawPostPayload(
                platform="Telegram",
                external_id="p7_e2e_tg_1",
                text="Flash alert: Rapid surge in public sector digital security discussions across channels #Security",
                author_username="intel_channel",
                author_display_name="Cyber Intelligence Channel",
                posted_at=now - timedelta(hours=1),
                language="en",
                url="https://t.me/intel_channel/p7_e2e_tg_1",
                metrics={"likes": 90, "comments": 15, "shares": 45, "views": 3200},
            ),
            # YouTube Video Post
            RawPostPayload(
                platform="YouTube",
                external_id="p7_e2e_yt_1",
                text="Deep-dive tutorial on real-time sentiment distribution and narrative emergence modeling #AI #DataScience",
                author_username="tech_educator",
                author_display_name="AI & Analytics Academy",
                posted_at=now - timedelta(hours=8),
                language="en",
                url="https://youtube.com/watch?v=p7_e2e_yt_1",
                metrics={"likes": 1500, "comments": 230, "shares": 310, "views": 45000},
            ),
        ]

        cls.ingested_ids = []
        for raw in cls.seed_posts:
            norm = cls.normalizer.normalize(raw)
            post = cls.ingestion_service.ingest_post(norm)
            cls.ingested_ids.append(post.post_id)

    @classmethod
    def tearDownClass(cls):
        """Cleanup seed data."""
        if hasattr(cls, "ingested_ids") and cls.ingested_ids:
            try:
                cls.db.query(Post).filter(Post.id.in_(cls.ingested_ids)).delete(synchronize_session=False)
                cls.db.commit()
            except Exception:
                cls.db.rollback()
        cls.db.close()

    # 1. System Health & Gateway Verification
    def test_e2e_health_gateway(self):
        status_code, data = call_api("GET", "/api/v1/health")
        self.assertEqual(status_code, 200)
        self.assertEqual(data["status"], "ok")
        self.assertIn("services", data)
        self.assertEqual(data["services"].get("analytics"), "ok")

    # 2. Executive Dashboard Overview End-to-End Contract
    def test_e2e_dashboard_overview_contract(self):
        status_code, data = call_api("GET", "/api/v1/analytics/overview")
        self.assertEqual(status_code, 200)
        self.assertGreaterEqual(data["total_posts"], len(self.seed_posts))
        self.assertIn("platforms", data)
        self.assertIn("sentiment", data)
        self.assertIn("topics", data)
        self.assertIn("trends", data)
        self.assertIn("network", data)

        # Verify platform breakdown contains ingested platforms
        platform_names = {p["platform"] for p in data["platforms"]}
        self.assertTrue({"X", "Reddit", "Telegram", "YouTube"}.issubset(platform_names))

    # 3. Filtered Overview by Platform
    def test_e2e_dashboard_overview_platform_filter(self):
        status_code, data = call_api("GET", "/api/v1/analytics/overview?platform=X")
        self.assertEqual(status_code, 200)
        self.assertGreaterEqual(data["total_posts"], 2)

    # 4. Multi-granularity Timeline Contract
    def test_e2e_timeline_granularity_contracts(self):
        # Hour granularity
        status_h, data_h = call_api("GET", "/api/v1/timeline?granularity=hour")
        self.assertEqual(status_h, 200)
        self.assertEqual(data_h["granularity"], "hour")
        self.assertIn("buckets", data_h)

        # Day granularity
        status_d, data_d = call_api("GET", "/api/v1/timeline?granularity=day")
        self.assertEqual(status_d, 200)
        self.assertEqual(data_d["granularity"], "day")

        # Week granularity
        status_w, data_w = call_api("GET", "/api/v1/timeline?granularity=week")
        self.assertEqual(status_w, 200)
        self.assertEqual(data_w["granularity"], "week")

    # 5. Timeline with Platform Filter
    def test_e2e_timeline_platform_filter(self):
        status_code, data = call_api("GET", "/api/v1/timeline?platform=Telegram&granularity=day")
        self.assertEqual(status_code, 200)
        self.assertIn("buckets", data)

    # 6. Posts Explorer Querying, Search, and Filtering
    def test_e2e_posts_explorer_contracts(self):
        # Default paginated list
        status_code, data = call_api("GET", "/api/v1/posts?limit=10&offset=0")
        self.assertEqual(status_code, 200)
        self.assertIn("total", data)
        self.assertIn("items", data)
        self.assertLessEqual(len(data["items"]), 10)

        # Keyword search
        status_s, data_s = call_api("GET", "/api/v1/posts?search=cybersecurity")
        self.assertEqual(status_s, 200)
        self.assertGreaterEqual(len(data_s["items"]), 1)
        self.assertIn("cybersecurity", data_s["items"][0]["text"].lower())

        # Author filter
        status_a, data_a = call_api("GET", "/api/v1/posts?author=threat_analyst")
        self.assertEqual(status_a, 200)
        self.assertGreaterEqual(len(data_a["items"]), 1)
        self.assertEqual(data_a["items"][0]["author_username"], "threat_analyst")

        # Single post retrieval
        post_id = self.ingested_ids[0]
        status_p, data_p = call_api("GET", f"/api/v1/posts/{post_id}")
        self.assertEqual(status_p, 200)
        self.assertEqual(data_p["id"], post_id)
        self.assertIn("metrics", data_p)

    # 7. Trends Radar Analytics Contract
    def test_e2e_trends_radar_contract(self):
        status_code, data = call_api("GET", "/api/v1/analytics/trends")
        self.assertEqual(status_code, 200)
        self.assertIn("trends", data)
        self.assertIn("total_topics_evaluated", data)
        self.assertIn("model", data)

    # 8. Network Graph & Influence Analysis Contract
    def test_e2e_network_graph_contract(self):
        status_code, data = call_api("GET", "/api/v1/analytics/network")
        self.assertEqual(status_code, 200)
        self.assertIn("nodes", data)
        self.assertIn("edges", data)
        self.assertIn("total_nodes", data)
        self.assertIn("total_edges", data)

    # 9. Multi-Platform Comparative Analytics
    def test_e2e_platform_comparison_contract(self):
        status_code, data = call_api("GET", "/api/v1/analytics/platforms/compare")
        self.assertEqual(status_code, 200)
        self.assertIn("platforms", data)
        self.assertIn("total_platforms", data)
        self.assertGreaterEqual(data["total_platforms"], 4)

    # 10. Platform Registry List
    def test_e2e_platforms_list(self):
        status_code, data = call_api("GET", "/api/v1/platforms")
        self.assertEqual(status_code, 200)
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 4)

    # 11. Error and Edge-Case Graceful Handling
    def test_e2e_error_handling_resilience(self):
        # Invalid date range (start > end)
        now = datetime.now(timezone.utc)
        start = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        end = (now - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
        status_code, data = call_api("GET", f"/api/v1/posts?start_date={start}&end_date={end}")
        self.assertEqual(status_code, 400)
        self.assertIn("detail", data)

        # Invalid sort_by field
        status_sort, data_sort = call_api("GET", "/api/v1/posts?sort_by=invalid_col")
        self.assertEqual(status_sort, 400)

        # Invalid timeline granularity
        status_gran, data_gran = call_api("GET", "/api/v1/timeline?granularity=decade")
        self.assertEqual(status_gran, 400)

        # Non-existent post ID returns 404
        status_404, data_404 = call_api("GET", "/api/v1/posts/99999999")
        self.assertEqual(status_404, 404)

        # Zero results search returns 200 with empty items list (not 500 error)
        status_empty, data_empty = call_api("GET", "/api/v1/posts?search=nonexistent_gibberish_string_xyz123")
        self.assertEqual(status_empty, 200)
        self.assertEqual(data_empty["total"], 0)
        self.assertEqual(len(data_empty["items"]), 0)


if __name__ == "__main__":
    unittest.main()
