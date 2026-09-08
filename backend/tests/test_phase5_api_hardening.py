import asyncio
from datetime import datetime, timedelta, timezone
import json
import unittest

from app.database import SessionLocal, engine
from app.main import app
from app.models.base import Base
from app.models.metric import PostMetric
from app.models.platform import Platform
from app.models.post import Post
from app.models.user import User


def call_api(method: str, path: str, body: dict = None) -> tuple[int, dict]:
    """Helper to simulate FastAPI HTTP calls without starting a live server."""
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


class TestPhase5APIHardening(unittest.TestCase):
    """Hardening and end-to-end workflow test suite for Phase 5 FastAPI application."""

    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.db = SessionLocal()
        cls._seed_test_database()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    @classmethod
    def _seed_test_database(cls):
        """Seeds canonical platforms, users, and posts for hardening verification."""
        p_x = cls.db.query(Platform).filter(Platform.name == "X").first()
        if not p_x:
            p_x = Platform(name="X")
            cls.db.add(p_x)
        p_tg = cls.db.query(Platform).filter(Platform.name == "Telegram").first()
        if not p_tg:
            p_tg = Platform(name="Telegram")
            cls.db.add(p_tg)
        cls.db.commit()

        u1 = cls.db.query(User).filter(User.username == "harden_user_1").first()
        if not u1:
            u1 = User(platform_id=p_x.id, username="harden_user_1", display_name="Harden User One")
            cls.db.add(u1)
            cls.db.commit()

        base_time = datetime(2026, 9, 8, 12, 0, 0)
        p1 = cls.db.query(Post).filter(Post.external_post_id == "harden_p1").first()
        if not p1:
            p1 = Post(
                platform_id=p_x.id,
                user_id=u1.id,
                external_post_id="harden_p1",
                text="Artificial Intelligence and Machine Learning in production. #AI #Tech",
                posted_at=base_time,
                collected_at=base_time,
                language="en",
                url="https://example.com/harden1",
            )
            cls.db.add(p1)
            cls.db.commit()

            m1 = PostMetric(post_id=p1.id, likes=100, comments=20, shares=15, views=1000, collected_at=base_time)
            cls.db.add(m1)

        p2 = cls.db.query(Post).filter(Post.external_post_id == "harden_p2").first()
        if not p2:
            p2 = Post(
                platform_id=p_tg.id,
                user_id=u1.id,
                external_post_id="harden_p2",
                text="Clean energy transition is accelerating worldwide. #EV #GreenEnergy",
                posted_at=base_time + timedelta(hours=2),
                collected_at=base_time + timedelta(hours=2),
                language="en",
                url="https://example.com/harden2",
            )
            cls.db.add(p2)
            cls.db.commit()

            m2 = PostMetric(post_id=p2.id, likes=200, comments=40, shares=30, views=2000, collected_at=base_time + timedelta(hours=2))
            cls.db.add(m2)

        cls.db.commit()

    # --- 1. Multi-Parameter Combination Tests ---

    def test_combined_filters_posts(self):
        start = "2026-09-08T00:00:00Z"
        end = "2026-09-09T00:00:00Z"
        path = f"/api/v1/posts?platform=X&language=en&search=Artificial&start_date={start}&end_date={end}&sort_by=posted_at&order=desc&limit=10&offset=0"
        status, data = call_api("GET", path)
        self.assertEqual(status, 200)
        self.assertGreaterEqual(data["total"], 1)

    def test_pagination_boundary_limit_1(self):
        status, data = call_api("GET", "/api/v1/posts?limit=1&offset=0")
        self.assertEqual(status, 200)
        self.assertEqual(data["limit"], 1)
        self.assertLessEqual(len(data["items"]), 1)

    def test_pagination_boundary_max_limit(self):
        status, data = call_api("GET", "/api/v1/posts?limit=200&offset=0")
        self.assertEqual(status, 200)
        self.assertEqual(data["limit"], 200)

    def test_pagination_offset_out_of_bounds(self):
        status, data = call_api("GET", "/api/v1/posts?limit=10&offset=100000")
        self.assertEqual(status, 200)
        self.assertEqual(len(data["items"]), 0)

    # --- 2. Platform Handling Tests ---

    def test_platform_alias_and_casing(self):
        status1, data1 = call_api("GET", "/api/v1/posts?platform=x")
        status2, data2 = call_api("GET", "/api/v1/posts?platform=X")
        self.assertEqual(status1, 200)
        self.assertEqual(status2, 200)
        self.assertEqual(data1["total"], data2["total"])

    # --- 3. Empty / Zero-Match Filter Resilience ---

    def test_zero_matching_filter_resilience(self):
        status, data = call_api("GET", "/api/v1/posts?search=non_existent_search_query_xyz_999")
        self.assertEqual(status, 200)
        self.assertEqual(data["total"], 0)
        self.assertEqual(data["items"], [])

    def test_timeline_empty_filter_resilience(self):
        status, data = call_api("GET", "/api/v1/timeline?platform=Telegram&start_date=2020-01-01T00:00:00Z&end_date=2020-01-02T00:00:00Z")
        self.assertEqual(status, 200)
        self.assertEqual(data["total_posts"], 0)
        self.assertEqual(data["buckets"], [])

    # --- 4. Cross-Endpoint Data Consistency ---

    def test_cross_endpoint_count_consistency(self):
        start = "2026-09-08T00:00:00Z"
        end = "2026-09-08T23:59:59Z"

        status_p, data_p = call_api("GET", f"/api/v1/posts?start_date={start}&end_date={end}")
        status_t, data_t = call_api("GET", f"/api/v1/timeline?start_date={start}&end_date={end}")
        status_o, data_o = call_api("GET", f"/api/v1/analytics/overview?start_date={start}&end_date={end}")

        self.assertEqual(status_p, 200)
        self.assertEqual(status_t, 200)
        self.assertEqual(status_o, 200)

        total_posts_posts_api = data_p["total"]
        total_posts_timeline_api = data_t["total_posts"]
        total_posts_overview_api = data_o["total_posts"]

        self.assertEqual(total_posts_posts_api, total_posts_timeline_api)
        self.assertEqual(total_posts_timeline_api, total_posts_overview_api)

    # --- 5. End-to-End Dashboard Workflows ---

    def test_e2e_dashboard_full_flow(self):
        # Step 1: Discover platforms
        s1, d1 = call_api("GET", "/api/v1/platforms")
        self.assertEqual(s1, 200)
        self.assertGreater(len(d1), 0)

        # Step 2: Fetch post feed
        s2, d2 = call_api("GET", "/api/v1/posts?limit=10")
        self.assertEqual(s2, 200)

        # Step 3: Fetch activity timeline
        s3, d3 = call_api("GET", "/api/v1/timeline?granularity=hour")
        self.assertEqual(s3, 200)

        # Step 4: Fetch sentiment analysis over DB posts
        s4, d4 = call_api("GET", "/api/v1/analytics/sentiment")
        self.assertEqual(s4, 200)

        # Step 5: Fetch topic clusters over DB posts
        s5, d5 = call_api("GET", "/api/v1/analytics/topics")
        self.assertEqual(s5, 200)

        # Step 6: Fetch trend momentum over DB posts
        s6, d6 = call_api("GET", "/api/v1/analytics/trends")
        self.assertEqual(s6, 200)

        # Step 7: Fetch network analysis over DB posts
        s7, d7 = call_api("GET", "/api/v1/analytics/network")
        self.assertEqual(s7, 200)

        # Step 8: Fetch high-level overview
        s8, d8 = call_api("GET", "/api/v1/analytics/overview")
        self.assertEqual(s8, 200)

        # Step 9: Fetch platform comparison
        s9, d9 = call_api("GET", "/api/v1/analytics/platforms/compare")
        self.assertEqual(s9, 200)

    def test_e2e_adhoc_post_analysis_flow(self):
        payload = {
            "raw_posts": [
                {
                    "platform": "twitter",
                    "external_id": "adhoc_1",
                    "text": "Cybersecurity threats spiking across cloud infrastructure. @security_team https://sec.example.com #CyberSecurity",
                    "posted_at": datetime.now(timezone.utc).isoformat(),
                }
            ]
        }
        # Step 1: Ad-hoc Sentiment
        s1, d1 = call_api("POST", "/api/v1/analytics/sentiment", payload)
        self.assertEqual(s1, 200)
        self.assertEqual(d1["total_analyzed"], 1)

        # Step 2: Ad-hoc Topics
        s2, d2 = call_api("POST", "/api/v1/analytics/topics", payload)
        self.assertEqual(s2, 200)
        self.assertIn("topics", d2)

        # Step 3: Ad-hoc Trends
        s3, d3 = call_api("POST", "/api/v1/analytics/trends", payload)
        self.assertEqual(s3, 200)
        self.assertIn("trends", d3)

        # Step 4: Ad-hoc Network
        s4, d4 = call_api("POST", "/api/v1/analytics/network", payload)
        self.assertEqual(s4, 200)
        self.assertGreater(d4["total_nodes"], 0)

        # Step 5: Unified Pipeline
        s5, d5 = call_api("POST", "/api/v1/analytics/analyze", payload)
        self.assertEqual(s5, 200)
        self.assertEqual(d5["valid_posts_count"], 1)

    # --- 6. Backward Compatibility & Health Verification ---

    def test_exact_health_response_contract(self):
        status, data = call_api("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(data, {"status": "ok"})

    def test_v1_health_response_contract(self):
        status, data = call_api("GET", "/api/v1/health")
        self.assertEqual(status, 200)
        self.assertEqual(data["status"], "ok")
        self.assertIn("version", data)
        self.assertIn("environment", data)


if __name__ == "__main__":
    unittest.main()
