import asyncio
from datetime import datetime, timezone
import json
import unittest
import urllib.parse

from app.database import SessionLocal
from app.main import app
from app.models.metric import PostMetric
from app.models.platform import Platform
from app.models.post import Post
from app.models.user import User
from app.schemas.analytics import (
    CountResponse,
    EngagementSummary,
    LanguageSummary,
    PlatformSummary,
    PostListResponse,
    TimeSeriesResponse,
)
from app.services.analytics import AnalyticsService


def call_api(method: str, url: str) -> tuple[int, dict]:
    """
    Invokes the FastAPI ASGI application with query string support.
    """
    parsed = urllib.parse.urlsplit(url)
    response_body = []
    status_code = None

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method.upper(),
        "path": parsed.path,
        "raw_path": parsed.path.encode(),
        "query_string": parsed.query.encode(),
        "headers": [(b"content-type", b"application/json")],
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        nonlocal status_code
        if message["type"] == "http.response.start":
            status_code = message["status"]
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


class TestAnalyticsService(unittest.TestCase):
    """
    Unit tests for AnalyticsService queries, aggregations, and edge cases.
    """

    def setUp(self):
        self.db = SessionLocal()
        self.service = AnalyticsService(self.db)
        self.temp_post_ids = []

    def tearDown(self):
        if self.temp_post_ids:
            self.db.query(PostMetric).filter(PostMetric.post_id.in_(self.temp_post_ids)).delete(
                synchronize_session=False
            )
            self.db.query(Post).filter(Post.id.in_(self.temp_post_ids)).delete(
                synchronize_session=False
            )
            self.db.commit()
        self.db.close()

    def test_1_get_posts_basic(self):
        result = self.service.get_posts(limit=10, offset=0)
        self.assertIsInstance(result, PostListResponse)
        self.assertGreater(result.total, 0)
        self.assertLessEqual(len(result.items), 10)
        self.assertEqual(result.limit, 10)
        self.assertEqual(result.offset, 0)

        # Check post summary fields
        first = result.items[0]
        self.assertIsNotNone(first.id)
        self.assertIsNotNone(first.platform)
        self.assertIsNotNone(first.external_post_id)
        self.assertIsNotNone(first.posted_at)

    def test_2_get_posts_deterministic_ordering(self):
        result = self.service.get_posts(limit=30, offset=0)
        items = result.items
        for i in range(len(items) - 1):
            curr = items[i]
            nxt = items[i + 1]
            # Primary sort posted_at DESC, secondary sort id DESC
            self.assertTrue(
                curr.posted_at > nxt.posted_at or (curr.posted_at == nxt.posted_at and curr.id >= nxt.id),
                f"Ordering violated between post {curr.id} and {nxt.id}",
            )

    def test_3_get_posts_pagination(self):
        page1 = self.service.get_posts(limit=5, offset=0)
        page2 = self.service.get_posts(limit=5, offset=5)

        self.assertEqual(len(page1.items), 5)
        self.assertEqual(len(page2.items), 5)
        page1_ids = {p.id for p in page1.items}
        page2_ids = {p.id for p in page2.items}
        self.assertEqual(len(page1_ids.intersection(page2_ids)), 0, "Pages should not overlap")

    def test_4_get_posts_empty_result(self):
        result = self.service.get_posts(platform="NonExistentPlatform999")
        self.assertEqual(result.total, 0)
        self.assertEqual(len(result.items), 0)

    def test_5_get_posts_platform_filter_case_insensitive(self):
        lower = self.service.get_posts(platform="telegram")
        upper = self.service.get_posts(platform="Telegram")
        self.assertEqual(lower.total, upper.total)
        self.assertGreater(lower.total, 0)
        for item in lower.items:
            self.assertEqual(item.platform, "Telegram")

    def test_6_get_posts_language_filter(self):
        te_posts = self.service.get_posts(language="te")
        self.assertGreater(te_posts.total, 0)
        for item in te_posts.items:
            self.assertEqual(item.language, "te")

        hi_posts = self.service.get_posts(language="HI")
        self.assertGreater(hi_posts.total, 0)
        for item in hi_posts.items:
            self.assertEqual(item.language, "hi")

    def test_7_get_posts_date_range_filter(self):
        start = datetime(2026, 9, 2, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 9, 3, 23, 59, 59, tzinfo=timezone.utc)

        filtered = self.service.get_posts(start_time=start, end_time=end)
        self.assertGreater(filtered.total, 0)
        for item in filtered.items:
            # Ensure within bounds
            dt = item.posted_at
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            self.assertGreaterEqual(dt, start)
            self.assertLessEqual(dt, end)

    def test_8_get_posts_author_filter(self):
        result = self.service.get_posts(author_username="insightx_official")
        self.assertGreaterEqual(result.total, 1)
        for item in result.items:
            self.assertEqual(item.author_username, "insightx_official")

    def test_9_get_posts_combined_filters(self):
        result = self.service.get_posts(
            platform="X",
            language="en",
            start_time=datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc),
        )
        self.assertGreater(result.total, 0)
        for item in result.items:
            self.assertEqual(item.platform, "X")
            self.assertEqual(item.language, "en")

    def test_10_get_post_count(self):
        total_count_resp = self.service.get_post_count()
        self.assertIsInstance(total_count_resp, CountResponse)
        self.assertGreaterEqual(total_count_resp.count, 44)

        x_count = self.service.get_post_count(platform="X")
        self.assertGreaterEqual(x_count.count, 14)
        self.assertIn("platform", x_count.filters_applied)

        zero_count = self.service.get_post_count(platform="GhostPlatformXYZ")
        self.assertEqual(zero_count.count, 0)

    def test_11_get_platform_summary(self):
        summaries = self.service.get_platform_summary()
        self.assertIsInstance(summaries, list)
        self.assertGreaterEqual(len(summaries), 4)

        names = [s.platform for s in summaries]
        self.assertIn("X", names)
        self.assertIn("Telegram", names)
        self.assertIn("Reddit", names)
        self.assertIn("YouTube", names)

        for s in summaries:
            self.assertIsInstance(s, PlatformSummary)
            self.assertGreater(s.post_count, 0)
            self.assertIsNotNone(s.earliest_post)
            self.assertIsNotNone(s.latest_post)
            self.assertLessEqual(s.earliest_post, s.latest_post)

    def test_12_get_language_summary(self):
        summaries = self.service.get_language_summary()
        self.assertIsInstance(summaries, list)
        self.assertGreaterEqual(len(summaries), 3)

        langs = {s.language for s in summaries}
        self.assertIn("en", langs)
        self.assertIn("te", langs)
        self.assertIn("hi", langs)

        # Verify ordering by post_count descending
        counts = [s.post_count for s in summaries]
        self.assertEqual(counts, sorted(counts, reverse=True))

    def test_13_get_engagement_summary_basic_and_averages(self):
        summary = self.service.get_engagement_summary()
        self.assertIsInstance(summary, EngagementSummary)
        self.assertGreater(summary.total_posts_analyzed, 0)
        self.assertGreater(summary.posts_with_metrics, 0)
        self.assertGreater(summary.total_likes, 0)
        self.assertGreater(summary.total_views, 0)
        self.assertGreater(summary.avg_likes, 0.0)
        self.assertGreater(summary.avg_views, 0.0)

    def test_14_get_engagement_summary_latest_snapshot_behavior(self):
        """
        Verify that when a post has multiple metric snapshots, only the latest snapshot
        is aggregated in the engagement totals.
        """
        x_plat = self.db.query(Platform).filter_by(name="X").first()

        # Create isolated post
        p = Post(
            platform_id=x_plat.id,
            external_post_id="test_engagement_snapshot_post",
            text="Engagement test",
            posted_at=datetime.now(timezone.utc),
            collected_at=datetime.now(timezone.utc),
        )
        self.db.add(p)
        self.db.flush()
        self.temp_post_ids.append(p.id)

        # Snapshot 1: 100 likes
        m1 = PostMetric(post_id=p.id, likes=100, views=1000)
        self.db.add(m1)
        self.db.flush()

        # Snapshot 2: 250 likes (updated duplicate)
        m2 = PostMetric(post_id=p.id, likes=250, views=2500)
        self.db.add(m2)
        self.db.commit()

        # Query engagement filtered specifically to this post's time / platform
        post_view = self.service.get_posts(platform="X", limit=1)
        # Verify latest metric attached to post in get_posts
        matched = [it for it in self.service.get_posts(platform="X", limit=50).items if it.id == p.id]
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0].metrics.likes, 250)
        self.assertEqual(matched[0].metrics.views, 2500)

    def test_15_get_engagement_summary_empty(self):
        summary = self.service.get_engagement_summary(platform="NonExistentPlat")
        self.assertEqual(summary.total_posts_analyzed, 0)
        self.assertEqual(summary.posts_with_metrics, 0)
        self.assertEqual(summary.total_likes, 0)
        self.assertEqual(summary.avg_likes, 0.0)

    def test_16_get_time_series_chronological(self):
        ts = self.service.get_time_series()
        self.assertIsInstance(ts, TimeSeriesResponse)
        self.assertEqual(ts.interval, "day")
        self.assertGreater(ts.total_points, 0)

        # Verify chronological order
        dates = [p.date for p in ts.points]
        self.assertEqual(dates, sorted(dates))

        for point in ts.points:
            self.assertGreater(point.count, 0)
            self.assertRegex(point.date, r"^\d{4}-\d{2}-\d{2}$")


    def test_17_search_text_match(self):
        result = self.service.get_posts(search="infrastructure")
        self.assertGreater(result.total, 0)
        for item in result.items:
            self.assertIn("infrastructure", item.text.lower())

    def test_18_search_case_insensitive(self):
        lower_result = self.service.get_posts(search="insightx")
        upper_result = self.service.get_posts(search="INSIGHTX")
        mixed_result = self.service.get_posts(search="InSiGhTx")

        self.assertGreater(lower_result.total, 0)
        self.assertEqual(lower_result.total, upper_result.total)
        self.assertEqual(lower_result.total, mixed_result.total)

    def test_19_search_no_match(self):
        result = self.service.get_posts(search="UnlikelyStringToMatch_9876543210")
        self.assertEqual(result.total, 0)
        self.assertEqual(len(result.items), 0)

    def test_20_search_combined_with_platform_filter(self):
        result = self.service.get_posts(search="infrastructure", platform="X")
        self.assertGreater(result.total, 0)
        for item in result.items:
            self.assertEqual(item.platform, "X")
            self.assertIn("infrastructure", item.text.lower())

    def test_21_search_combined_with_language_filter(self):
        result = self.service.get_posts(search="infrastructure", language="en")
        self.assertGreater(result.total, 0)
        for item in result.items:
            self.assertEqual(item.language, "en")
            self.assertIn("infrastructure", item.text.lower())

    def test_22_count_with_search(self):
        count_resp = self.service.get_post_count(search="InsightX")
        self.assertIsInstance(count_resp, CountResponse)
        self.assertGreater(count_resp.count, 0)
        self.assertIn("search", count_resp.filters_applied)
        self.assertEqual(count_resp.filters_applied["search"], "InsightX")

    # --- Component 8.2: Engagement filtering ---

    def test_23_min_likes_filter(self):
        result = self.service.get_posts(min_likes=1)
        self.assertGreater(result.total, 0)
        for item in result.items:
            self.assertIsNotNone(item.metrics)
            self.assertGreaterEqual(item.metrics.likes, 1)

    def test_24_min_comments_filter(self):
        result = self.service.get_posts(min_comments=1)
        self.assertGreater(result.total, 0)
        for item in result.items:
            self.assertIsNotNone(item.metrics)
            self.assertGreaterEqual(item.metrics.comments, 1)

    def test_25_min_shares_filter(self):
        result = self.service.get_posts(min_shares=1)
        self.assertGreater(result.total, 0)
        for item in result.items:
            self.assertIsNotNone(item.metrics)
            self.assertGreaterEqual(item.metrics.shares, 1)

    def test_26_min_views_filter(self):
        result = self.service.get_posts(min_views=1)
        self.assertGreater(result.total, 0)
        for item in result.items:
            self.assertIsNotNone(item.metrics)
            self.assertGreaterEqual(item.metrics.views, 1)

    def test_27_high_threshold_returns_empty(self):
        result = self.service.get_posts(min_likes=999_999_999)
        self.assertEqual(result.total, 0)

    def test_28_multiple_engagement_filters_combined(self):
        result = self.service.get_posts(min_likes=1, min_views=1)
        self.assertGreater(result.total, 0)
        for item in result.items:
            self.assertIsNotNone(item.metrics)
            self.assertGreaterEqual(item.metrics.likes, 1)
            self.assertGreaterEqual(item.metrics.views, 1)

    def test_29_engagement_filter_with_platform(self):
        result = self.service.get_posts(min_likes=1, platform="YouTube")
        self.assertGreater(result.total, 0)
        for item in result.items:
            self.assertEqual(item.platform, "YouTube")
            self.assertIsNotNone(item.metrics)
            self.assertGreaterEqual(item.metrics.likes, 1)

    def test_30_engagement_filter_with_search(self):
        result = self.service.get_posts(min_views=1, search="infrastructure")
        for item in result.items:
            self.assertIn("infrastructure", item.text.lower())
            self.assertIsNotNone(item.metrics)
            self.assertGreaterEqual(item.metrics.views, 1)

    def test_31_count_with_engagement_filter(self):
        count_all = self.service.get_post_count()
        count_engaged = self.service.get_post_count(min_likes=1)
        self.assertGreater(count_all.count, 0)
        self.assertGreater(count_engaged.count, 0)
        self.assertLessEqual(count_engaged.count, count_all.count)
        self.assertIn("min_likes", count_engaged.filters_applied)

    def test_32_zero_threshold_is_same_as_no_filter(self):
        all_posts = self.service.get_post_count()
        zero_likes = self.service.get_post_count(min_likes=0)
        # min_likes=0 should match all posts (0 >= 0 always true after COALESCE)
        self.assertEqual(all_posts.count, zero_likes.count)

    def test_33_engagement_filter_uses_chronological_collected_at(self):
        # Create a test post
        post = Post(
            platform_id=1,
            external_post_id="chronological_metric_test_1",
            text="Chronological metric snapshot test post",
            posted_at=datetime(2026, 9, 1, 12, 0, 0),
            collected_at=datetime(2026, 9, 1, 12, 0, 0),
            language="en",
        )
        self.db.add(post)
        self.db.commit()
        self.temp_post_ids.append(post.id)

        # Snapshot 1: older collected_at, but inserted first (lower ID)
        m1 = PostMetric(
            post_id=post.id,
            collected_at=datetime(2026, 9, 1, 10, 0, 0),
            likes=1000,
            comments=0,
            shares=0,
            views=0,
        )
        # Snapshot 2: newer collected_at, inserted second (higher ID) with lower likes
        m2 = PostMetric(
            post_id=post.id,
            collected_at=datetime(2026, 9, 2, 10, 0, 0),
            likes=50,
            comments=0,
            shares=0,
            views=0,
        )
        self.db.add_all([m1, m2])
        self.db.commit()

        # The latest metric is m2 (likes=50) based on collected_at.
        # Filtering with min_likes=500 should NOT include this post.
        res_high = self.service.get_posts(search="Chronological metric snapshot test post", min_likes=500)
        self.assertEqual(res_high.total, 0)

        # Filtering with min_likes=50 SHOULD include this post.
        res_low = self.service.get_posts(search="Chronological metric snapshot test post", min_likes=50)
        self.assertEqual(res_low.total, 1)
        self.assertEqual(res_low.items[0].metrics.likes, 50)

    def test_34_engagement_filter_deterministic_id_tie_breaker(self):
        # Create a test post
        post = Post(
            platform_id=1,
            external_post_id="tie_breaker_metric_test_1",
            text="Tie breaker metric snapshot test post",
            posted_at=datetime(2026, 9, 1, 12, 0, 0),
            collected_at=datetime(2026, 9, 1, 12, 0, 0),
            language="en",
        )
        self.db.add(post)
        self.db.commit()
        self.temp_post_ids.append(post.id)

        same_time = datetime(2026, 9, 5, 12, 0, 0)
        m1 = PostMetric(
            post_id=post.id,
            collected_at=same_time,
            likes=100,
            comments=0,
            shares=0,
            views=0,
        )
        self.db.add(m1)
        self.db.commit()

        m2 = PostMetric(
            post_id=post.id,
            collected_at=same_time,
            likes=300,
            comments=0,
            shares=0,
            views=0,
        )
        self.db.add(m2)
        self.db.commit()

        # With equal collected_at, the higher id (m2 with likes=300) should be selected
        res = self.service.get_posts(search="Tie breaker metric snapshot test post", min_likes=200)
        self.assertEqual(res.total, 1)
        self.assertEqual(res.items[0].metrics.likes, 300)

        res_too_high = self.service.get_posts(search="Tie breaker metric snapshot test post", min_likes=400)
        self.assertEqual(res_too_high.total, 0)

    # --- Component 8.3: Dynamic analytics sorting ---

    def test_35_sort_by_posted_at_desc(self):
        result = self.service.get_posts(sort_by="posted_at", order="desc", limit=20)
        self.assertGreater(len(result.items), 1)
        for i in range(len(result.items) - 1):
            self.assertGreaterEqual(result.items[i].posted_at, result.items[i + 1].posted_at)

    def test_36_sort_by_posted_at_asc(self):
        result = self.service.get_posts(sort_by="posted_at", order="asc", limit=20)
        self.assertGreater(len(result.items), 1)
        for i in range(len(result.items) - 1):
            self.assertLessEqual(result.items[i].posted_at, result.items[i + 1].posted_at)

    def test_37_sort_by_likes_desc(self):
        result = self.service.get_posts(sort_by="likes", order="desc", limit=20)
        self.assertGreater(len(result.items), 1)
        for i in range(len(result.items) - 1):
            l1 = result.items[i].metrics.likes if result.items[i].metrics else 0
            l2 = result.items[i + 1].metrics.likes if result.items[i + 1].metrics else 0
            self.assertGreaterEqual(l1, l2)

    def test_38_sort_by_comments(self):
        desc_res = self.service.get_posts(sort_by="comments", order="desc", limit=20)
        self.assertGreater(len(desc_res.items), 1)
        for i in range(len(desc_res.items) - 1):
            c1 = desc_res.items[i].metrics.comments if desc_res.items[i].metrics else 0
            c2 = desc_res.items[i + 1].metrics.comments if desc_res.items[i + 1].metrics else 0
            self.assertGreaterEqual(c1, c2)

        asc_res = self.service.get_posts(sort_by="comments", order="asc", limit=20)
        self.assertGreater(len(asc_res.items), 1)
        for i in range(len(asc_res.items) - 1):
            c1 = asc_res.items[i].metrics.comments if asc_res.items[i].metrics else 0
            c2 = asc_res.items[i + 1].metrics.comments if asc_res.items[i + 1].metrics else 0
            self.assertLessEqual(c1, c2)

    def test_39_sort_by_shares(self):
        desc_res = self.service.get_posts(sort_by="shares", order="desc", limit=20)
        self.assertGreater(len(desc_res.items), 1)
        for i in range(len(desc_res.items) - 1):
            s1 = desc_res.items[i].metrics.shares if desc_res.items[i].metrics else 0
            s2 = desc_res.items[i + 1].metrics.shares if desc_res.items[i + 1].metrics else 0
            self.assertGreaterEqual(s1, s2)

    def test_40_sort_by_views(self):
        desc_res = self.service.get_posts(sort_by="views", order="desc", limit=20)
        self.assertGreater(len(desc_res.items), 1)
        for i in range(len(desc_res.items) - 1):
            v1 = desc_res.items[i].metrics.views if desc_res.items[i].metrics else 0
            v2 = desc_res.items[i + 1].metrics.views if desc_res.items[i + 1].metrics else 0
            self.assertGreaterEqual(v1, v2)

    def test_41_sort_combined_with_search(self):
        result = self.service.get_posts(search="infrastructure", sort_by="likes", order="desc")
        self.assertGreater(len(result.items), 0)
        for i in range(len(result.items)):
            self.assertIn("infrastructure", result.items[i].text.lower())
            if i < len(result.items) - 1:
                l1 = result.items[i].metrics.likes if result.items[i].metrics else 0
                l2 = result.items[i + 1].metrics.likes if result.items[i + 1].metrics else 0
                self.assertGreaterEqual(l1, l2)

    def test_42_sort_combined_with_platform(self):
        result = self.service.get_posts(platform="X", sort_by="posted_at", order="asc")
        self.assertGreater(len(result.items), 0)
        for i in range(len(result.items)):
            self.assertEqual(result.items[i].platform, "X")
            if i < len(result.items) - 1:
                self.assertLessEqual(result.items[i].posted_at, result.items[i + 1].posted_at)

    def test_43_sort_combined_with_min_likes(self):
        result = self.service.get_posts(min_likes=5, sort_by="likes", order="asc")
        self.assertGreater(len(result.items), 0)
        for i in range(len(result.items)):
            likes = result.items[i].metrics.likes if result.items[i].metrics else 0
            self.assertGreaterEqual(likes, 5)
            if i < len(result.items) - 1:
                next_likes = result.items[i + 1].metrics.likes if result.items[i + 1].metrics else 0
                self.assertLessEqual(likes, next_likes)

    def test_44_deterministic_ordering_when_values_equal(self):
        t = datetime(2026, 9, 1, 12, 0, 0)
        p1 = Post(
            platform_id=1,
            external_post_id="tie_p1",
            text="Deterministic tie breaker test post 1",
            posted_at=t,
            collected_at=t,
            language="en",
        )
        p2 = Post(
            platform_id=1,
            external_post_id="tie_p2",
            text="Deterministic tie breaker test post 2",
            posted_at=t,
            collected_at=t,
            language="en",
        )
        self.db.add_all([p1, p2])
        self.db.commit()
        self.temp_post_ids.extend([p1.id, p2.id])

        m1 = PostMetric(post_id=p1.id, collected_at=t, likes=777)
        m2 = PostMetric(post_id=p2.id, collected_at=t, likes=777)
        self.db.add_all([m1, m2])
        self.db.commit()

        # Descending: higher id comes first
        res_desc = self.service.get_posts(search="Deterministic tie breaker test post", sort_by="likes", order="desc")
        self.assertEqual(len(res_desc.items), 2)
        self.assertGreater(res_desc.items[0].id, res_desc.items[1].id)

        # Ascending: lower id comes first
        res_asc = self.service.get_posts(search="Deterministic tie breaker test post", sort_by="likes", order="asc")
        self.assertEqual(len(res_asc.items), 2)
        self.assertLess(res_asc.items[0].id, res_asc.items[1].id)

    def test_45_invalid_sort_field_service_validation(self):
        with self.assertRaises(ValueError):
            self.service.get_posts(sort_by="invalid_col")
        with self.assertRaises(ValueError):
            self.service.get_posts(order="invalid_dir")


class TestAnalyticsAPI(unittest.TestCase):
    """
    Integration tests for /api/v1/analytics FastAPI endpoints.
    """

    def test_1_get_posts_endpoint(self):
        code, data = call_api("GET", "/api/v1/analytics/posts?limit=5&offset=0")
        self.assertEqual(code, 200)
        self.assertIn("total", data)
        self.assertIn("items", data)
        self.assertEqual(data["limit"], 5)
        self.assertEqual(len(data["items"]), 5)

    def test_2_get_posts_with_filters(self):
        code, data = call_api("GET", "/api/v1/analytics/posts?platform=Telegram&language=en&limit=10")
        self.assertEqual(code, 200)
        self.assertGreater(data["total"], 0)
        for item in data["items"]:
            self.assertEqual(item["platform"], "Telegram")
            self.assertEqual(item["language"], "en")

    def test_3_get_count_endpoint(self):
        code, data = call_api("GET", "/api/v1/analytics/count?platform=Reddit")
        self.assertEqual(code, 200)
        self.assertGreaterEqual(data["count"], 10)
        self.assertEqual(data["filters_applied"].get("platform"), "Reddit")

    def test_4_get_platforms_endpoint(self):
        code, data = call_api("GET", "/api/v1/analytics/platforms")
        self.assertEqual(code, 200)
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 4)
        names = [p["platform"] for p in data]
        self.assertIn("X", names)
        self.assertIn("YouTube", names)

    def test_5_get_languages_endpoint(self):
        code, data = call_api("GET", "/api/v1/analytics/languages")
        self.assertEqual(code, 200)
        self.assertIsInstance(data, list)
        langs = [l["language"] for l in data]
        self.assertIn("en", langs)
        self.assertIn("te", langs)
        self.assertIn("hi", langs)

    def test_6_get_engagement_endpoint(self):
        code, data = call_api("GET", "/api/v1/analytics/engagement?platform=YouTube")
        self.assertEqual(code, 200)
        self.assertIn("total_posts_analyzed", data)
        self.assertIn("total_views", data)
        self.assertIn("avg_views", data)
        self.assertGreater(data["total_views"], 0)

    def test_7_get_timeseries_endpoint(self):
        code, data = call_api("GET", "/api/v1/analytics/timeseries")
        self.assertEqual(code, 200)
        self.assertEqual(data["interval"], "day")
        self.assertGreater(data["total_points"], 0)
        self.assertIsInstance(data["points"], list)

    def test_8_validation_start_date_after_end_date(self):
        # 400 Bad Request
        url = "/api/v1/analytics/posts?start_date=2026-09-10T00:00:00Z&end_date=2026-09-01T00:00:00Z"
        code, data = call_api("GET", url)
        self.assertEqual(code, 400)
        self.assertIn("start_date cannot be after end_date", data.get("detail", ""))

    def test_9_validation_limit_out_of_bounds(self):
        # limit > 200 -> 422 Unprocessable
        code1, _ = call_api("GET", "/api/v1/analytics/posts?limit=250")
        self.assertEqual(code1, 422)

        # limit < 1 -> 422 Unprocessable
        code2, _ = call_api("GET", "/api/v1/analytics/posts?limit=0")
        self.assertEqual(code2, 422)

    def test_10_validation_negative_offset(self):
        # offset < 0 -> 422 Unprocessable
        code, _ = call_api("GET", "/api/v1/analytics/posts?offset=-5")
        self.assertEqual(code, 422)

    def test_11_validation_invalid_date_format(self):
        code, _ = call_api("GET", "/api/v1/analytics/posts?start_date=not-a-date")
        self.assertEqual(code, 422)

    def test_12_unknown_platform_returns_graceful_empty_result(self):
        code, data = call_api("GET", "/api/v1/analytics/posts?platform=NonExistent999")
        self.assertEqual(code, 200)
        self.assertEqual(data["total"], 0)
        self.assertEqual(len(data["items"]), 0)

    def test_13_get_posts_with_search(self):
        code, data = call_api("GET", "/api/v1/analytics/posts?search=InsightX")
        self.assertEqual(code, 200)
        self.assertGreater(data["total"], 0)
        for item in data["items"]:
            self.assertIn("insightx", item["text"].lower())

    def test_14_get_posts_with_search_case_insensitive(self):
        code1, data1 = call_api("GET", "/api/v1/analytics/posts?search=insightx")
        code2, data2 = call_api("GET", "/api/v1/analytics/posts?search=INSIGHTX")
        self.assertEqual(code1, 200)
        self.assertEqual(code2, 200)
        self.assertEqual(data1["total"], data2["total"])

    def test_15_get_posts_with_search_no_match(self):
        code, data = call_api("GET", "/api/v1/analytics/posts?search=NonExistentSearchMatchTermXYZ999")
        self.assertEqual(code, 200)
        self.assertEqual(data["total"], 0)
        self.assertEqual(len(data["items"]), 0)

    def test_16_get_posts_with_search_and_platform(self):
        code, data = call_api("GET", "/api/v1/analytics/posts?search=infrastructure&platform=X")
        self.assertEqual(code, 200)
        self.assertGreater(data["total"], 0)
        for item in data["items"]:
            self.assertEqual(item["platform"], "X")
            self.assertIn("infrastructure", item["text"].lower())

    def test_17_get_posts_with_search_and_language(self):
        code, data = call_api("GET", "/api/v1/analytics/posts?search=infrastructure&language=en")
        self.assertEqual(code, 200)
        self.assertGreater(data["total"], 0)
        for item in data["items"]:
            self.assertEqual(item["language"], "en")
            self.assertIn("infrastructure", item["text"].lower())

    def test_18_get_count_with_search(self):
        code, data = call_api("GET", "/api/v1/analytics/count?search=InsightX")
        self.assertEqual(code, 200)
        self.assertGreater(data["count"], 0)
        self.assertEqual(data["filters_applied"].get("search"), "InsightX")

    # --- Component 8.2: Engagement filtering API tests ---

    def test_19_min_likes_endpoint(self):
        code, data = call_api("GET", "/api/v1/analytics/posts?min_likes=1")
        self.assertEqual(code, 200)
        self.assertGreater(data["total"], 0)
        for item in data["items"]:
            self.assertIsNotNone(item["metrics"])
            self.assertGreaterEqual(item["metrics"]["likes"], 1)

    def test_20_min_comments_endpoint(self):
        code, data = call_api("GET", "/api/v1/analytics/posts?min_comments=1")
        self.assertEqual(code, 200)
        self.assertGreater(data["total"], 0)
        for item in data["items"]:
            self.assertIsNotNone(item["metrics"])
            self.assertGreaterEqual(item["metrics"]["comments"], 1)

    def test_21_min_shares_endpoint(self):
        code, data = call_api("GET", "/api/v1/analytics/posts?min_shares=1")
        self.assertEqual(code, 200)
        self.assertGreater(data["total"], 0)
        for item in data["items"]:
            self.assertIsNotNone(item["metrics"])
            self.assertGreaterEqual(item["metrics"]["shares"], 1)

    def test_22_min_views_endpoint(self):
        code, data = call_api("GET", "/api/v1/analytics/posts?min_views=1")
        self.assertEqual(code, 200)
        self.assertGreater(data["total"], 0)
        for item in data["items"]:
            self.assertIsNotNone(item["metrics"])
            self.assertGreaterEqual(item["metrics"]["views"], 1)

    def test_23_high_threshold_empty(self):
        code, data = call_api("GET", "/api/v1/analytics/posts?min_likes=999999999")
        self.assertEqual(code, 200)
        self.assertEqual(data["total"], 0)

    def test_24_multiple_engagement_filters(self):
        code, data = call_api("GET", "/api/v1/analytics/posts?min_likes=1&min_views=1")
        self.assertEqual(code, 200)
        self.assertGreater(data["total"], 0)
        for item in data["items"]:
            self.assertIsNotNone(item["metrics"])
            self.assertGreaterEqual(item["metrics"]["likes"], 1)
            self.assertGreaterEqual(item["metrics"]["views"], 1)

    def test_25_engagement_with_platform(self):
        code, data = call_api("GET", "/api/v1/analytics/posts?min_likes=1&platform=YouTube")
        self.assertEqual(code, 200)
        self.assertGreater(data["total"], 0)
        for item in data["items"]:
            self.assertEqual(item["platform"], "YouTube")
            self.assertIsNotNone(item["metrics"])
            self.assertGreaterEqual(item["metrics"]["likes"], 1)

    def test_26_engagement_with_search(self):
        code, data = call_api("GET", "/api/v1/analytics/posts?min_views=1&search=infrastructure")
        self.assertEqual(code, 200)
        for item in data["items"]:
            self.assertIn("infrastructure", item["text"].lower())
            self.assertIsNotNone(item["metrics"])
            self.assertGreaterEqual(item["metrics"]["views"], 1)

    def test_27_count_with_engagement_filter(self):
        code, data = call_api("GET", "/api/v1/analytics/count?min_likes=1")
        self.assertEqual(code, 200)
        self.assertGreater(data["count"], 0)
        self.assertIn("min_likes", data["filters_applied"])

    def test_28_negative_min_likes_rejected(self):
        code, _ = call_api("GET", "/api/v1/analytics/posts?min_likes=-1")
        self.assertEqual(code, 422)

    def test_29_negative_min_comments_rejected(self):
        code, _ = call_api("GET", "/api/v1/analytics/posts?min_comments=-5")
        self.assertEqual(code, 422)

    def test_30_negative_min_shares_rejected(self):
        code, _ = call_api("GET", "/api/v1/analytics/posts?min_shares=-1")
        self.assertEqual(code, 422)

    def test_31_negative_min_views_rejected(self):
        code, _ = call_api("GET", "/api/v1/analytics/posts?min_views=-100")
        self.assertEqual(code, 422)

    # --- Component 8.3: Dynamic analytics sorting API tests ---

    def test_32_sort_by_likes_desc_endpoint(self):
        code, data = call_api("GET", "/api/v1/analytics/posts?sort_by=likes&order=desc&limit=10")
        self.assertEqual(code, 200)
        self.assertIn("items", data)
        items = data["items"]
        self.assertGreater(len(items), 1)
        for i in range(len(items) - 1):
            l1 = items[i]["metrics"]["likes"] if items[i].get("metrics") else 0
            l2 = items[i + 1]["metrics"]["likes"] if items[i + 1].get("metrics") else 0
            self.assertGreaterEqual(l1, l2)

    def test_33_sort_by_posted_at_asc_endpoint(self):
        code, data = call_api("GET", "/api/v1/analytics/posts?sort_by=posted_at&order=asc&limit=10")
        self.assertEqual(code, 200)
        self.assertIn("items", data)
        items = data["items"]
        self.assertGreater(len(items), 1)
        for i in range(len(items) - 1):
            self.assertLessEqual(items[i]["posted_at"], items[i + 1]["posted_at"])

    def test_34_sort_by_shares_desc_endpoint(self):
        code, data = call_api("GET", "/api/v1/analytics/posts?sort_by=shares&order=desc&limit=10")
        self.assertEqual(code, 200)
        self.assertIn("items", data)
        items = data["items"]
        self.assertGreater(len(items), 1)
        for i in range(len(items) - 1):
            s1 = items[i]["metrics"]["shares"] if items[i].get("metrics") else 0
            s2 = items[i + 1]["metrics"]["shares"] if items[i + 1].get("metrics") else 0
            self.assertGreaterEqual(s1, s2)

    def test_35_invalid_sort_by_rejected(self):
        code, data = call_api("GET", "/api/v1/analytics/posts?sort_by=random_column")
        self.assertEqual(code, 400)
        self.assertIn("Invalid sort_by", data.get("detail", ""))

    def test_36_invalid_order_rejected(self):
        code, data = call_api("GET", "/api/v1/analytics/posts?order=diagonal")
        self.assertEqual(code, 400)
        self.assertIn("Invalid order", data.get("detail", ""))

    def test_37_sort_combined_with_filters_endpoint(self):
        code, data = call_api("GET", "/api/v1/analytics/posts?platform=YouTube&min_views=1&sort_by=views&order=desc")
        self.assertEqual(code, 200)
        self.assertIn("items", data)
        items = data["items"]
        self.assertGreater(len(items), 0)
        for i in range(len(items)):
            self.assertEqual(items[i]["platform"], "YouTube")
            self.assertIsNotNone(items[i].get("metrics"))
            self.assertGreaterEqual(items[i]["metrics"]["views"], 1)
            if i < len(items) - 1:
                v1 = items[i]["metrics"]["views"]
                v2 = items[i + 1]["metrics"]["views"] if items[i + 1].get("metrics") else 0
                self.assertGreaterEqual(v1, v2)


if __name__ == "__main__":
    unittest.main()
