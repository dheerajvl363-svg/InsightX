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
from app.models.topic import PostTopic, Topic
from app.models.user import User
from app.schemas.analytics import (
    AuthorListResponse,
    AuthorSummary,
    CountResponse,
    EngagementSummary,
    LanguageSummary,
    PlatformSummary,
    PostListResponse,
    TimeSeriesResponse,
    TopicListResponse,
    TopicSummary,
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
        self.temp_user_ids = []
        self.temp_topic_ids = []

    def tearDown(self):
        if self.temp_post_ids:
            self.db.query(PostMetric).filter(PostMetric.post_id.in_(self.temp_post_ids)).delete(
                synchronize_session=False
            )
            self.db.query(PostTopic).filter(PostTopic.post_id.in_(self.temp_post_ids)).delete(
                synchronize_session=False
            )
            self.db.query(Post).filter(Post.id.in_(self.temp_post_ids)).delete(
                synchronize_session=False
            )
            self.db.commit()
        if hasattr(self, "temp_topic_ids") and self.temp_topic_ids:
            self.db.query(Topic).filter(Topic.id.in_(self.temp_topic_ids)).delete(
                synchronize_session=False
            )
            self.db.commit()
        if hasattr(self, "temp_user_ids") and self.temp_user_ids:
            self.db.query(User).filter(User.id.in_(self.temp_user_ids)).delete(
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

    # --- Component 8.4: Author Analytics Aggregation service tests ---

    def test_46_author_summary_basic(self):
        res = self.service.get_author_summary(limit=5, offset=0)
        self.assertIsInstance(res, AuthorListResponse)
        self.assertGreater(res.total, 0)
        self.assertEqual(res.limit, 5)
        self.assertEqual(res.offset, 0)
        self.assertLessEqual(len(res.items), 5)
        item = res.items[0]
        self.assertIsInstance(item, AuthorSummary)
        self.assertIsNotNone(item.username)
        self.assertIsNotNone(item.platform)
        self.assertGreater(item.post_count, 0)
        self.assertGreaterEqual(item.total_likes, 0)
        self.assertGreaterEqual(item.total_comments, 0)
        self.assertGreaterEqual(item.total_shares, 0)
        self.assertGreaterEqual(item.total_views, 0)
        self.assertGreaterEqual(item.avg_likes, 0.0)
        self.assertGreaterEqual(item.avg_comments, 0.0)
        self.assertGreaterEqual(item.avg_shares, 0.0)
        self.assertGreaterEqual(item.avg_views, 0.0)
        self.assertIsNotNone(item.earliest_post)
        self.assertIsNotNone(item.latest_post)

    def test_47_author_summary_multiple_posts_and_averages(self):
        u = User(platform_id=1, username="c84_multi_author", display_name="Multi Author")
        self.db.add(u)
        self.db.commit()
        self.temp_user_ids.append(u.id)

        t1 = datetime(2026, 1, 1, 10, 0, 0)
        t2 = datetime(2026, 1, 2, 10, 0, 0)
        p1 = Post(
            platform_id=1,
            user_id=u.id,
            external_post_id="c84_p1",
            text="c84_multi_post_keyword post 1",
            posted_at=t1,
            collected_at=t1,
            language="en",
        )
        p2 = Post(
            platform_id=1,
            user_id=u.id,
            external_post_id="c84_p2",
            text="c84_multi_post_keyword post 2",
            posted_at=t2,
            collected_at=t2,
            language="en",
        )
        self.db.add_all([p1, p2])
        self.db.commit()
        self.temp_post_ids.extend([p1.id, p2.id])

        m1 = PostMetric(post_id=p1.id, collected_at=t1, likes=100, comments=10, shares=4, views=1000)
        m2 = PostMetric(post_id=p2.id, collected_at=t2, likes=200, comments=30, shares=16, views=3000)
        self.db.add_all([m1, m2])
        self.db.commit()

        res = self.service.get_author_summary(search="c84_multi_post_keyword")
        self.assertEqual(res.total, 1)
        self.assertEqual(len(res.items), 1)
        author = res.items[0]
        self.assertEqual(author.username, "c84_multi_author")
        self.assertEqual(author.display_name, "Multi Author")
        self.assertEqual(author.platform, "X")
        self.assertEqual(author.post_count, 2)
        self.assertEqual(author.total_likes, 300)
        self.assertEqual(author.total_comments, 40)
        self.assertEqual(author.total_shares, 20)
        self.assertEqual(author.total_views, 4000)
        self.assertEqual(author.avg_likes, 150.0)
        self.assertEqual(author.avg_comments, 20.0)
        self.assertEqual(author.avg_shares, 10.0)
        self.assertEqual(author.avg_views, 2000.0)
        self.assertEqual(author.earliest_post, t1)
        self.assertEqual(author.latest_post, t2)

    def test_48_author_summary_post_without_metrics(self):
        u = User(platform_id=1, username="c84_no_metric_author", display_name="No Metric")
        self.db.add(u)
        self.db.commit()
        self.temp_user_ids.append(u.id)

        t = datetime(2026, 1, 3, 10, 0, 0)
        p = Post(
            platform_id=1,
            user_id=u.id,
            external_post_id="c84_no_metric_p",
            text="c84_no_metric_keyword text",
            posted_at=t,
            collected_at=t,
            language="en",
        )
        self.db.add(p)
        self.db.commit()
        self.temp_post_ids.append(p.id)

        res = self.service.get_author_summary(search="c84_no_metric_keyword")
        self.assertEqual(res.total, 1)
        author = res.items[0]
        self.assertEqual(author.post_count, 1)
        self.assertEqual(author.total_likes, 0)
        self.assertEqual(author.total_comments, 0)
        self.assertEqual(author.total_shares, 0)
        self.assertEqual(author.total_views, 0)
        self.assertEqual(author.avg_likes, 0.0)
        self.assertEqual(author.avg_comments, 0.0)
        self.assertEqual(author.avg_shares, 0.0)
        self.assertEqual(author.avg_views, 0.0)

    def test_49_author_summary_multiple_snapshots_latest_collected_at_wins(self):
        u = User(platform_id=1, username="c84_snap_author", display_name="Snapshot Author")
        self.db.add(u)
        self.db.commit()
        self.temp_user_ids.append(u.id)

        t = datetime(2026, 1, 4, 10, 0, 0)
        p = Post(
            platform_id=1,
            user_id=u.id,
            external_post_id="c84_snap_p",
            text="c84_snap_keyword text",
            posted_at=t,
            collected_at=t,
            language="en",
        )
        self.db.add(p)
        self.db.commit()
        self.temp_post_ids.append(p.id)

        # Older snapshot: collected earlier with MORE likes
        m_older = PostMetric(post_id=p.id, collected_at=datetime(2026, 1, 4, 11, 0, 0), likes=888)
        # Newer snapshot: collected later with FEWER likes
        m_newer = PostMetric(post_id=p.id, collected_at=datetime(2026, 1, 4, 12, 0, 0), likes=77)
        self.db.add_all([m_older, m_newer])
        self.db.commit()

        res = self.service.get_author_summary(search="c84_snap_keyword")
        self.assertEqual(res.total, 1)
        author = res.items[0]
        # Only the newer snapshot must contribute (77), not 888 and not 888+77=965
        self.assertEqual(author.total_likes, 77)
        self.assertEqual(author.avg_likes, 77.0)

    def test_50_author_summary_multiple_snapshots_tie_breaker_id_wins(self):
        u = User(platform_id=1, username="c84_tie_snap_author", display_name="Tie Snap Author")
        self.db.add(u)
        self.db.commit()
        self.temp_user_ids.append(u.id)

        t = datetime(2026, 1, 5, 10, 0, 0)
        p = Post(
            platform_id=1,
            user_id=u.id,
            external_post_id="c84_tie_snap_p",
            text="c84_tie_snap_keyword text",
            posted_at=t,
            collected_at=t,
            language="en",
        )
        self.db.add(p)
        self.db.commit()
        self.temp_post_ids.append(p.id)

        # Exact same collected_at timestamp
        snap_time = datetime(2026, 1, 5, 12, 0, 0)
        m1 = PostMetric(post_id=p.id, collected_at=snap_time, likes=100)
        self.db.add(m1)
        self.db.commit()

        m2 = PostMetric(post_id=p.id, collected_at=snap_time, likes=450)
        self.db.add(m2)
        self.db.commit()
        # m2.id > m1.id, so m2 wins
        self.assertGreater(m2.id, m1.id)

        res = self.service.get_author_summary(search="c84_tie_snap_keyword")
        self.assertEqual(res.total, 1)
        author = res.items[0]
        self.assertEqual(author.total_likes, 450)

    def test_51_author_summary_platform_filter(self):
        res = self.service.get_author_summary(platform="Telegram")
        self.assertGreater(res.total, 0)
        for author in res.items:
            self.assertEqual(author.platform, "Telegram")

    def test_52_author_summary_language_filter(self):
        res = self.service.get_author_summary(language="te")
        self.assertGreater(res.total, 0)
        usernames = {a.username for a in res.items}
        self.assertIn("telugu_science_hub", usernames)

    def test_53_author_summary_date_filter(self):
        start = datetime(2026, 9, 2, 0, 0, 0)
        end = datetime(2026, 9, 2, 23, 59, 59)
        res = self.service.get_author_summary(start_date=start, end_date=end)
        self.assertGreater(res.total, 0)
        for author in res.items:
            self.assertGreaterEqual(author.earliest_post, start)
            self.assertLessEqual(author.latest_post, end)

    def test_54_author_summary_search_filter(self):
        res = self.service.get_author_summary(search="ISRO")
        self.assertGreater(res.total, 0)
        for a in res.items:
            self.assertGreater(a.post_count, 0)

    def test_55_author_summary_sort_post_count_desc_and_asc(self):
        desc = self.service.get_author_summary(sort_by="post_count", order="desc", limit=10)
        for i in range(len(desc.items) - 1):
            self.assertGreaterEqual(desc.items[i].post_count, desc.items[i + 1].post_count)

        asc = self.service.get_author_summary(sort_by="post_count", order="asc", limit=10)
        for i in range(len(asc.items) - 1):
            self.assertLessEqual(asc.items[i].post_count, asc.items[i + 1].post_count)

    def test_56_author_summary_sort_total_likes_and_views(self):
        likes_desc = self.service.get_author_summary(sort_by="total_likes", order="desc", limit=10)
        for i in range(len(likes_desc.items) - 1):
            self.assertGreaterEqual(likes_desc.items[i].total_likes, likes_desc.items[i + 1].total_likes)

        views_desc = self.service.get_author_summary(sort_by="total_views", order="desc", limit=10)
        for i in range(len(views_desc.items) - 1):
            self.assertGreaterEqual(views_desc.items[i].total_views, views_desc.items[i + 1].total_views)

    def test_57_author_summary_pagination(self):
        page1 = self.service.get_author_summary(limit=3, offset=0)
        page2 = self.service.get_author_summary(limit=3, offset=3)
        self.assertEqual(len(page1.items), 3)
        self.assertEqual(len(page2.items), 3)
        p1_authors = {(a.username, a.platform) for a in page1.items}
        p2_authors = {(a.username, a.platform) for a in page2.items}
        self.assertEqual(len(p1_authors.intersection(p2_authors)), 0)

    def test_58_author_summary_deterministic_ordering_tie_breaker(self):
        u1 = User(platform_id=1, username="c84_tie_author_aaa", display_name="AAA")
        u2 = User(platform_id=1, username="c84_tie_author_zzz", display_name="ZZZ")
        self.db.add_all([u1, u2])
        self.db.commit()
        self.temp_user_ids.extend([u1.id, u2.id])

        t = datetime(2026, 1, 6, 10, 0, 0)
        p1 = Post(
            platform_id=1,
            user_id=u1.id,
            external_post_id="c84_tie_p1",
            text="c84_det_tie_keyword p1",
            posted_at=t,
            collected_at=t,
            language="en",
        )
        p2 = Post(
            platform_id=1,
            user_id=u2.id,
            external_post_id="c84_tie_p2",
            text="c84_det_tie_keyword p2",
            posted_at=t,
            collected_at=t,
            language="en",
        )
        self.db.add_all([p1, p2])
        self.db.commit()
        self.temp_post_ids.extend([p1.id, p2.id])

        # Same metrics
        m1 = PostMetric(post_id=p1.id, collected_at=t, likes=333)
        m2 = PostMetric(post_id=p2.id, collected_at=t, likes=333)
        self.db.add_all([m1, m2])
        self.db.commit()

        res_desc = self.service.get_author_summary(search="c84_det_tie_keyword", sort_by="total_likes", order="desc")
        self.assertEqual(len(res_desc.items), 2)
        # Descending: username zzz before aaa
        self.assertEqual(res_desc.items[0].username, "c84_tie_author_zzz")
        self.assertEqual(res_desc.items[1].username, "c84_tie_author_aaa")

        res_asc = self.service.get_author_summary(search="c84_det_tie_keyword", sort_by="total_likes", order="asc")
        self.assertEqual(len(res_asc.items), 2)
        # Ascending: username aaa before zzz
        self.assertEqual(res_asc.items[0].username, "c84_tie_author_aaa")
        self.assertEqual(res_asc.items[1].username, "c84_tie_author_zzz")

    def test_59_author_summary_invalid_sort_and_order_validation(self):
        with self.assertRaises(ValueError):
            self.service.get_author_summary(sort_by="unsupported_column")
        with self.assertRaises(ValueError):
            self.service.get_author_summary(order="upside_down")

    def test_60_author_summary_combined_filters_and_sorting(self):
        res = self.service.get_author_summary(
            platform="YouTube",
            language="en",
            search="India",
            sort_by="total_likes",
            order="desc",
        )
        self.assertIsInstance(res, AuthorListResponse)
        for a in res.items:
            self.assertEqual(a.platform, "YouTube")
        for i in range(len(res.items) - 1):
            self.assertGreaterEqual(res.items[i].total_likes, res.items[i + 1].total_likes)

    def test_topic_summary_basic_aggregation(self):
        u = User(platform_id=1, username="c85_topic_user", display_name="Topic User")
        self.db.add(u)
        self.db.commit()
        self.temp_user_ids.append(u.id)

        t1 = datetime(2026, 1, 1, 10, 0, 0)
        t2 = datetime(2026, 1, 2, 10, 0, 0)
        p1 = Post(
            platform_id=1,
            user_id=u.id,
            external_post_id="c85_tp1",
            text="Topic post 1",
            posted_at=t1,
            collected_at=t1,
            language="en",
        )
        p2 = Post(
            platform_id=1,
            user_id=u.id,
            external_post_id="c85_tp2",
            text="Topic post 2",
            posted_at=t2,
            collected_at=t2,
            language="en",
        )
        self.db.add_all([p1, p2])
        self.db.commit()
        self.temp_post_ids.extend([p1.id, p2.id])

        topic_a = Topic(name="topic_analytics_test_a")
        topic_b = Topic(name="topic_analytics_test_b")
        self.db.add_all([topic_a, topic_b])
        self.db.commit()
        self.temp_topic_ids.extend([topic_a.id, topic_b.id])

        pt1 = PostTopic(post_id=p1.id, topic_id=topic_a.id)
        pt2 = PostTopic(post_id=p2.id, topic_id=topic_a.id)
        pt3 = PostTopic(post_id=p2.id, topic_id=topic_b.id)
        self.db.add_all([pt1, pt2, pt3])
        self.db.commit()

        m1 = PostMetric(post_id=p1.id, collected_at=t1, likes=100, comments=10, shares=5, views=1000)
        m2 = PostMetric(post_id=p2.id, collected_at=t2, likes=50, comments=5, shares=2, views=500)
        self.db.add_all([m1, m2])
        self.db.commit()

        res = self.service.get_topic_summary()
        self.assertEqual(res.total, 2)

        topic_map = {item.topic_name: item for item in res.items}
        self.assertIn("topic_analytics_test_a", topic_map)
        self.assertIn("topic_analytics_test_b", topic_map)

        item_a = topic_map["topic_analytics_test_a"]
        self.assertEqual(item_a.post_count, 2)
        self.assertEqual(item_a.total_likes, 150)
        self.assertEqual(item_a.total_comments, 15)
        self.assertEqual(item_a.total_shares, 7)
        self.assertEqual(item_a.total_views, 1500)
        self.assertEqual(item_a.avg_likes, 75.0)
        self.assertEqual(item_a.avg_comments, 7.5)
        self.assertEqual(item_a.avg_shares, 3.5)
        self.assertEqual(item_a.avg_views, 750.0)

        item_b = topic_map["topic_analytics_test_b"]
        self.assertEqual(item_b.post_count, 1)
        self.assertEqual(item_b.total_likes, 50)
        self.assertEqual(item_b.total_comments, 5)
        self.assertEqual(item_b.total_shares, 2)
        self.assertEqual(item_b.total_views, 500)
        self.assertEqual(item_b.avg_likes, 50.0)
        self.assertEqual(item_b.avg_comments, 5.0)
        self.assertEqual(item_b.avg_shares, 2.0)
        self.assertEqual(item_b.avg_views, 500.0)

    def test_topic_summary_uses_latest_metric_snapshot(self):
        u = User(platform_id=1, username="c85_topic_user_snapshot", display_name="Snapshot User")
        self.db.add(u)
        self.db.commit()
        self.temp_user_ids.append(u.id)

        t = datetime(2026, 1, 1, 9, 0, 0)
        p = Post(
            platform_id=1,
            user_id=u.id,
            external_post_id="c85_snap_p1",
            text="Topic snapshot post",
            posted_at=t,
            collected_at=t,
            language="en",
        )
        self.db.add(p)
        self.db.commit()
        self.temp_post_ids.append(p.id)

        topic = Topic(name="topic_analytics_snapshot_test")
        self.db.add(topic)
        self.db.commit()
        self.temp_topic_ids.append(topic.id)

        pt = PostTopic(post_id=p.id, topic_id=topic.id)
        self.db.add(pt)
        self.db.commit()

        m_older = PostMetric(
            post_id=p.id,
            collected_at=datetime(2026, 1, 1, 10, 0, 0),
            likes=10,
            comments=2,
            shares=1,
            views=100,
        )
        m_newer = PostMetric(
            post_id=p.id,
            collected_at=datetime(2026, 1, 2, 10, 0, 0),
            likes=100,
            comments=20,
            shares=10,
            views=1000,
        )
        self.db.add_all([m_older, m_newer])
        self.db.commit()

        res = self.service.get_topic_summary()
        topic_map = {item.topic_name: item for item in res.items}
        self.assertIn("topic_analytics_snapshot_test", topic_map)

        item = topic_map["topic_analytics_snapshot_test"]
        self.assertEqual(item.post_count, 1)
        self.assertEqual(item.total_likes, 100)
        self.assertEqual(item.total_comments, 20)
        self.assertEqual(item.total_shares, 10)
        self.assertEqual(item.total_views, 1000)
        self.assertEqual(item.avg_likes, 100.0)
        self.assertEqual(item.avg_comments, 20.0)
        self.assertEqual(item.avg_shares, 10.0)
        self.assertEqual(item.avg_views, 1000.0)

        # Assert older snapshot values were not summed
        self.assertNotEqual(item.total_likes, 110)
        self.assertNotEqual(item.total_comments, 22)
        self.assertNotEqual(item.total_shares, 11)
        self.assertNotEqual(item.total_views, 1100)

    def test_topic_summary_counts_posts_without_metrics(self):
        u = User(platform_id=1, username="c85_topic_user_no_metric", display_name="No Metric User")
        self.db.add(u)
        self.db.commit()
        self.temp_user_ids.append(u.id)

        t1 = datetime(2026, 1, 1, 10, 0, 0)
        t2 = datetime(2026, 1, 2, 10, 0, 0)
        p1 = Post(
            platform_id=1,
            user_id=u.id,
            external_post_id="c85_nm_p1",
            text="Topic with metric post",
            posted_at=t1,
            collected_at=t1,
            language="en",
        )
        p2 = Post(
            platform_id=1,
            user_id=u.id,
            external_post_id="c85_nm_p2",
            text="Topic without metric post",
            posted_at=t2,
            collected_at=t2,
            language="en",
        )
        self.db.add_all([p1, p2])
        self.db.commit()
        self.temp_post_ids.extend([p1.id, p2.id])

        topic = Topic(name="topic_analytics_no_metric_test")
        self.db.add(topic)
        self.db.commit()
        self.temp_topic_ids.append(topic.id)

        pt1 = PostTopic(post_id=p1.id, topic_id=topic.id)
        pt2 = PostTopic(post_id=p2.id, topic_id=topic.id)
        self.db.add_all([pt1, pt2])
        self.db.commit()

        m1 = PostMetric(post_id=p1.id, collected_at=t1, likes=100, comments=10, shares=5, views=1000)
        self.db.add(m1)
        self.db.commit()

        res = self.service.get_topic_summary()
        topic_map = {item.topic_name: item for item in res.items}
        self.assertIn("topic_analytics_no_metric_test", topic_map)

        item = topic_map["topic_analytics_no_metric_test"]
        self.assertEqual(item.post_count, 2)
        self.assertEqual(item.total_likes, 100)
        self.assertEqual(item.total_comments, 10)
        self.assertEqual(item.total_shares, 5)
        self.assertEqual(item.total_views, 1000)
        self.assertEqual(item.avg_likes, 50.0)
        self.assertEqual(item.avg_comments, 5.0)
        self.assertEqual(item.avg_shares, 2.5)
        self.assertEqual(item.avg_views, 500.0)

    def test_topic_summary_applies_post_filters(self):
        u1 = User(platform_id=1, username="c85_topic_filter_u1", display_name="Filter User 1")
        u2 = User(platform_id=1, username="c85_topic_filter_u2", display_name="Filter User 2")
        self.db.add_all([u1, u2])
        self.db.commit()
        self.temp_user_ids.extend([u1.id, u2.id])

        t1 = datetime(2026, 1, 10, 10, 0, 0)
        t2 = datetime(2026, 2, 10, 10, 0, 0)
        p1 = Post(
            platform_id=1,
            user_id=u1.id,
            external_post_id="c85_filter_p1",
            text="python analytics topic",
            posted_at=t1,
            collected_at=t1,
            language="en",
        )
        p2 = Post(
            platform_id=1,
            user_id=u2.id,
            external_post_id="c85_filter_p2",
            text="football topic",
            posted_at=t2,
            collected_at=t2,
            language="te",
        )
        self.db.add_all([p1, p2])
        self.db.commit()
        self.temp_post_ids.extend([p1.id, p2.id])

        topic = Topic(name="topic_analytics_filter_test")
        self.db.add(topic)
        self.db.commit()
        self.temp_topic_ids.append(topic.id)

        pt1 = PostTopic(post_id=p1.id, topic_id=topic.id)
        pt2 = PostTopic(post_id=p2.id, topic_id=topic.id)
        self.db.add_all([pt1, pt2])
        self.db.commit()

        m1 = PostMetric(post_id=p1.id, collected_at=t1, likes=100, comments=0, shares=0, views=0)
        m2 = PostMetric(post_id=p2.id, collected_at=t2, likes=50, comments=0, shares=0, views=0)
        self.db.add_all([m1, m2])
        self.db.commit()

        # 1. language="en" → only Post 1 should count
        res_lang = self.service.get_topic_summary(language="en")
        map_lang = {item.topic_name: item for item in res_lang.items}
        self.assertIn("topic_analytics_filter_test", map_lang)
        self.assertEqual(map_lang["topic_analytics_filter_test"].post_count, 1)
        self.assertEqual(map_lang["topic_analytics_filter_test"].total_likes, 100)

        # 2. search="python" → only Post 1 should count
        res_search = self.service.get_topic_summary(search="python")
        map_search = {item.topic_name: item for item in res_search.items}
        self.assertIn("topic_analytics_filter_test", map_search)
        self.assertEqual(map_search["topic_analytics_filter_test"].post_count, 1)
        self.assertEqual(map_search["topic_analytics_filter_test"].total_likes, 100)

        # 3. start_date=datetime(2026, 2, 1) → only Post 2 should count
        res_start = self.service.get_topic_summary(start_date=datetime(2026, 2, 1))
        map_start = {item.topic_name: item for item in res_start.items}
        self.assertIn("topic_analytics_filter_test", map_start)
        self.assertEqual(map_start["topic_analytics_filter_test"].post_count, 1)
        self.assertEqual(map_start["topic_analytics_filter_test"].total_likes, 50)

        # 4. start_date=datetime(2026, 1, 1), end_date=datetime(2026, 1, 31, 23, 59, 59) → only Post 1 should count
        res_range = self.service.get_topic_summary(
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31, 23, 59, 59),
        )
        map_range = {item.topic_name: item for item in res_range.items}
        self.assertIn("topic_analytics_filter_test", map_range)
        self.assertEqual(map_range["topic_analytics_filter_test"].post_count, 1)
        self.assertEqual(map_range["topic_analytics_filter_test"].total_likes, 100)

        # No filters → both posts count
        res_none = self.service.get_topic_summary()
        map_none = {item.topic_name: item for item in res_none.items}
        self.assertIn("topic_analytics_filter_test", map_none)
        self.assertEqual(map_none["topic_analytics_filter_test"].post_count, 2)
        self.assertEqual(map_none["topic_analytics_filter_test"].total_likes, 150)

    def test_topic_summary_sorting_and_pagination(self):
        u = User(platform_id=1, username="c85_topic_sort_user", display_name="Sort User")
        self.db.add(u)
        self.db.commit()
        self.temp_user_ids.append(u.id)

        t1 = datetime(2026, 1, 1, 10, 0, 0)
        t2 = datetime(2026, 1, 2, 10, 0, 0)
        t3 = datetime(2026, 1, 3, 10, 0, 0)

        p1 = Post(
            platform_id=1,
            user_id=u.id,
            external_post_id="c85_sort_p1",
            text="Topic sort post 1",
            posted_at=t1,
            collected_at=t1,
            language="en",
        )
        p2 = Post(
            platform_id=1,
            user_id=u.id,
            external_post_id="c85_sort_p2",
            text="Topic sort post 2",
            posted_at=t2,
            collected_at=t2,
            language="en",
        )
        p3 = Post(
            platform_id=1,
            user_id=u.id,
            external_post_id="c85_sort_p3",
            text="Topic sort post 3",
            posted_at=t3,
            collected_at=t3,
            language="en",
        )
        self.db.add_all([p1, p2, p3])
        self.db.commit()
        self.temp_post_ids.extend([p1.id, p2.id, p3.id])

        topic_a = Topic(name="topic_analytics_sort_a")
        topic_b = Topic(name="topic_analytics_sort_b")
        topic_c = Topic(name="topic_analytics_sort_c")
        self.db.add_all([topic_a, topic_b, topic_c])
        self.db.commit()
        self.temp_topic_ids.extend([topic_a.id, topic_b.id, topic_c.id])

        pt1 = PostTopic(post_id=p1.id, topic_id=topic_a.id)
        pt2 = PostTopic(post_id=p2.id, topic_id=topic_b.id)
        pt3 = PostTopic(post_id=p3.id, topic_id=topic_c.id)
        self.db.add_all([pt1, pt2, pt3])
        self.db.commit()

        m1 = PostMetric(post_id=p1.id, collected_at=t1, likes=100, comments=0, shares=0, views=0)
        m2 = PostMetric(post_id=p2.id, collected_at=t2, likes=300, comments=0, shares=0, views=0)
        m3 = PostMetric(post_id=p3.id, collected_at=t3, likes=200, comments=0, shares=0, views=0)
        self.db.add_all([m1, m2, m3])
        self.db.commit()

        # Sort total_likes desc → B, C, A
        res_desc = self.service.get_topic_summary(sort_by="total_likes", order="desc")
        self.assertEqual(res_desc.total, 3)
        self.assertEqual(
            [item.topic_name for item in res_desc.items],
            ["topic_analytics_sort_b", "topic_analytics_sort_c", "topic_analytics_sort_a"],
        )

        # Sort total_likes asc → A, C, B
        res_asc = self.service.get_topic_summary(sort_by="total_likes", order="asc")
        self.assertEqual(res_asc.total, 3)
        self.assertEqual(
            [item.topic_name for item in res_asc.items],
            ["topic_analytics_sort_a", "topic_analytics_sort_c", "topic_analytics_sort_b"],
        )

        # Pagination limit=2, offset=1 on desc → C, A
        res_page = self.service.get_topic_summary(sort_by="total_likes", order="desc", limit=2, offset=1)
        self.assertEqual(res_page.total, 3)
        self.assertEqual(res_page.limit, 2)
        self.assertEqual(res_page.offset, 1)
        self.assertEqual(len(res_page.items), 2)
        self.assertEqual(
            [item.topic_name for item in res_page.items],
            ["topic_analytics_sort_c", "topic_analytics_sort_a"],
        )

    def test_engagement_timeseries_basic_aggregation(self):
        u = User(platform_id=1, username="c86_ts_user_basic", display_name="TS Basic User")
        self.db.add(u)
        self.db.commit()
        self.temp_user_ids.append(u.id)

        t1_a = datetime(2026, 1, 10, 10, 0, 0)
        t1_b = datetime(2026, 1, 10, 15, 0, 0)
        t2 = datetime(2026, 1, 11, 12, 0, 0)

        p1 = Post(
            platform_id=1,
            user_id=u.id,
            external_post_id="c86_ts_p1",
            text="Day 1 post with metric",
            posted_at=t1_a,
            collected_at=t1_a,
            language="en",
        )
        p2 = Post(
            platform_id=1,
            user_id=u.id,
            external_post_id="c86_ts_p2",
            text="Day 1 post without metric",
            posted_at=t1_b,
            collected_at=t1_b,
            language="en",
        )
        p3 = Post(
            platform_id=1,
            user_id=u.id,
            external_post_id="c86_ts_p3",
            text="Day 2 post with metric",
            posted_at=t2,
            collected_at=t2,
            language="en",
        )
        self.db.add_all([p1, p2, p3])
        self.db.commit()
        self.temp_post_ids.extend([p1.id, p2.id, p3.id])

        m1 = PostMetric(post_id=p1.id, collected_at=t1_a, likes=100, comments=20, shares=10, views=1000)
        m3 = PostMetric(post_id=p3.id, collected_at=t2, likes=50, comments=5, shares=2, views=500)
        self.db.add_all([m1, m3])
        self.db.commit()

        res = self.service.get_engagement_time_series()
        self.assertEqual(res.interval, "day")

        point_map = {p.date: p for p in res.points}
        self.assertIn("2026-01-10", point_map)
        self.assertIn("2026-01-11", point_map)

        pt1 = point_map["2026-01-10"]
        self.assertEqual(pt1.post_count, 2)
        self.assertEqual(pt1.total_likes, 100)
        self.assertEqual(pt1.total_comments, 20)
        self.assertEqual(pt1.total_shares, 10)
        self.assertEqual(pt1.total_views, 1000)
        self.assertEqual(pt1.avg_likes, 50.0)
        self.assertEqual(pt1.avg_comments, 10.0)
        self.assertEqual(pt1.avg_shares, 5.0)
        self.assertEqual(pt1.avg_views, 500.0)

        pt2 = point_map["2026-01-11"]
        self.assertEqual(pt2.post_count, 1)
        self.assertEqual(pt2.total_likes, 50)
        self.assertEqual(pt2.total_comments, 5)
        self.assertEqual(pt2.total_shares, 2)
        self.assertEqual(pt2.total_views, 500)
        self.assertEqual(pt2.avg_likes, 50.0)

        dates = [p.date for p in res.points]
        self.assertEqual(dates, sorted(dates))

    def test_engagement_timeseries_uses_latest_metric_snapshot(self):
        u = User(platform_id=1, username="c86_ts_user_snap", display_name="TS Snap User")
        self.db.add(u)
        self.db.commit()
        self.temp_user_ids.append(u.id)

        t = datetime(2026, 1, 15, 10, 0, 0)
        p = Post(
            platform_id=1,
            user_id=u.id,
            external_post_id="c86_ts_snap_p1",
            text="Snapshot test post",
            posted_at=t,
            collected_at=t,
            language="en",
        )
        self.db.add(p)
        self.db.commit()
        self.temp_post_ids.append(p.id)

        m_older = PostMetric(post_id=p.id, collected_at=datetime(2026, 1, 15, 10, 0, 0), likes=10, comments=2, shares=1, views=100)
        m_newer = PostMetric(post_id=p.id, collected_at=datetime(2026, 1, 15, 12, 0, 0), likes=100, comments=20, shares=10, views=1000)
        self.db.add_all([m_older, m_newer])
        self.db.commit()

        res = self.service.get_engagement_time_series()
        point_map = {pt.date: pt for pt in res.points}
        self.assertIn("2026-01-15", point_map)
        pt = point_map["2026-01-15"]
        self.assertEqual(pt.post_count, 1)
        self.assertEqual(pt.total_likes, 100)
        self.assertEqual(pt.total_comments, 20)
        self.assertEqual(pt.total_shares, 10)
        self.assertEqual(pt.total_views, 1000)
        self.assertEqual(pt.avg_likes, 100.0)

    def test_engagement_timeseries_filters(self):
        u = User(platform_id=1, username="c86_ts_user_flt", display_name="TS Filter User")
        self.db.add(u)
        self.db.commit()
        self.temp_user_ids.append(u.id)

        t1 = datetime(2026, 1, 20, 10, 0, 0)
        t2 = datetime(2026, 2, 20, 10, 0, 0)
        p1 = Post(
            platform_id=1,
            user_id=u.id,
            external_post_id="c86_flt_p1",
            text="python machine learning trend",
            posted_at=t1,
            collected_at=t1,
            language="en",
        )
        p2 = Post(
            platform_id=1,
            user_id=u.id,
            external_post_id="c86_flt_p2",
            text="cricket match update",
            posted_at=t2,
            collected_at=t2,
            language="te",
        )
        self.db.add_all([p1, p2])
        self.db.commit()
        self.temp_post_ids.extend([p1.id, p2.id])

        m1 = PostMetric(post_id=p1.id, collected_at=t1, likes=100, comments=10, shares=5, views=1000)
        m2 = PostMetric(post_id=p2.id, collected_at=t2, likes=50, comments=5, shares=2, views=500)
        self.db.add_all([m1, m2])
        self.db.commit()

        # language="en" filter
        res_lang = self.service.get_engagement_time_series(language="en")
        map_lang = {pt.date: pt for pt in res_lang.points}
        self.assertIn("2026-01-20", map_lang)
        self.assertNotIn("2026-02-20", map_lang)
        self.assertEqual(map_lang["2026-01-20"].total_likes, 100)

        # search="cricket" filter
        res_srch = self.service.get_engagement_time_series(search="cricket")
        map_srch = {pt.date: pt for pt in res_srch.points}
        self.assertIn("2026-02-20", map_srch)
        self.assertNotIn("2026-01-20", map_srch)
        self.assertEqual(map_srch["2026-02-20"].total_likes, 50)

        # date range filter
        res_range = self.service.get_engagement_time_series(
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31, 23, 59, 59),
        )
        map_range = {pt.date: pt for pt in res_range.points}
        self.assertIn("2026-01-20", map_range)
        self.assertNotIn("2026-02-20", map_range)


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

    # --- Component 8.4: Author Analytics Aggregation API tests ---

    def test_38_get_authors_endpoint_basic(self):
        code, data = call_api("GET", "/api/v1/analytics/authors?limit=5&offset=0")
        self.assertEqual(code, 200)
        self.assertIn("total", data)
        self.assertIn("items", data)
        self.assertEqual(data["limit"], 5)
        self.assertEqual(data["offset"], 0)
        self.assertGreater(data["total"], 0)
        self.assertLessEqual(len(data["items"]), 5)
        item = data["items"][0]
        self.assertIn("username", item)
        self.assertIn("platform", item)
        self.assertIn("post_count", item)
        self.assertIn("total_likes", item)
        self.assertIn("total_comments", item)
        self.assertIn("total_shares", item)
        self.assertIn("total_views", item)
        self.assertIn("avg_likes", item)
        self.assertIn("avg_comments", item)
        self.assertIn("avg_shares", item)
        self.assertIn("avg_views", item)
        self.assertIn("earliest_post", item)
        self.assertIn("latest_post", item)

    def test_39_get_authors_endpoint_platform_filter(self):
        code, data = call_api("GET", "/api/v1/analytics/authors?platform=YouTube")
        self.assertEqual(code, 200)
        self.assertGreater(len(data["items"]), 0)
        for item in data["items"]:
            self.assertEqual(item["platform"], "YouTube")

    def test_40_get_authors_endpoint_sort_total_likes_desc(self):
        code, data = call_api("GET", "/api/v1/analytics/authors?sort_by=total_likes&order=desc&limit=10")
        self.assertEqual(code, 200)
        items = data["items"]
        self.assertGreater(len(items), 1)
        for i in range(len(items) - 1):
            self.assertGreaterEqual(items[i]["total_likes"], items[i + 1]["total_likes"])

    def test_41_get_authors_endpoint_sort_post_count_asc(self):
        code, data = call_api("GET", "/api/v1/analytics/authors?sort_by=post_count&order=asc&limit=10")
        self.assertEqual(code, 200)
        items = data["items"]
        self.assertGreater(len(items), 1)
        for i in range(len(items) - 1):
            self.assertLessEqual(items[i]["post_count"], items[i + 1]["post_count"])

    def test_42_get_authors_endpoint_invalid_sort_by_400(self):
        code, data = call_api("GET", "/api/v1/analytics/authors?sort_by=unsupported_metric")
        self.assertEqual(code, 400)
        self.assertIn("Invalid sort_by", data.get("detail", ""))

    def test_43_get_authors_endpoint_invalid_order_400(self):
        code, data = call_api("GET", "/api/v1/analytics/authors?order=backward")
        self.assertEqual(code, 400)
        self.assertIn("Invalid order", data.get("detail", ""))

    def test_44_get_authors_endpoint_invalid_date_range_400(self):
        code, data = call_api("GET", "/api/v1/analytics/authors?start_date=2026-12-01T00:00:00&end_date=2026-01-01T00:00:00")
        self.assertEqual(code, 400)
        self.assertIn("start_date cannot be after end_date", data.get("detail", ""))

    def test_45_get_authors_endpoint_combined_search_and_pagination(self):
        code, data = call_api("GET", "/api/v1/analytics/authors?search=india&limit=2&offset=0")
        self.assertEqual(code, 200)
        self.assertEqual(data["limit"], 2)
        self.assertEqual(data["offset"], 0)
        self.assertLessEqual(len(data["items"]), 2)

    # --- Component 8.5: Topic Analytics Aggregation API tests ---

    def test_46_get_topics_endpoint_basic(self):
        db = SessionLocal()
        try:
            u = User(platform_id=1, username="c85_api_topic_user_basic", display_name="Topic API User")
            db.add(u)
            db.commit()

            t1 = datetime(2026, 1, 1, 10, 0, 0)
            p = Post(
                platform_id=1,
                user_id=u.id,
                external_post_id="c85_api_basic_p1",
                text="API basic topic post",
                posted_at=t1,
                collected_at=t1,
                language="en",
            )
            db.add(p)
            db.commit()

            topic = Topic(name="topic_api_basic_test")
            db.add(topic)
            db.commit()

            pt = PostTopic(post_id=p.id, topic_id=topic.id)
            db.add(pt)
            db.commit()

            m = PostMetric(post_id=p.id, collected_at=t1, likes=150, comments=15, shares=5, views=1000)
            db.add(m)
            db.commit()

            code, data = call_api("GET", "/api/v1/analytics/topics?limit=5&offset=0")
            self.assertEqual(code, 200)
            self.assertIn("total", data)
            self.assertIn("items", data)
            self.assertEqual(data["limit"], 5)
            self.assertEqual(data["offset"], 0)
            self.assertGreaterEqual(data["total"], 1)

            topic_map = {item["topic_name"]: item for item in data["items"]}
            self.assertIn("topic_api_basic_test", topic_map)
            item = topic_map["topic_api_basic_test"]
            self.assertEqual(item["post_count"], 1)
            self.assertEqual(item["total_likes"], 150)
            self.assertEqual(item["total_comments"], 15)
            self.assertEqual(item["total_shares"], 5)
            self.assertEqual(item["total_views"], 1000)
            self.assertEqual(item["avg_likes"], 150.0)
            self.assertEqual(item["avg_comments"], 15.0)
            self.assertEqual(item["avg_shares"], 5.0)
            self.assertEqual(item["avg_views"], 1000.0)
            self.assertIn("earliest_post", item)
            self.assertIn("latest_post", item)
        finally:
            db.query(PostMetric).filter(PostMetric.post_id == p.id).delete()
            db.query(PostTopic).filter(PostTopic.post_id == p.id).delete()
            db.query(Post).filter(Post.id == p.id).delete()
            db.query(Topic).filter(Topic.id == topic.id).delete()
            db.query(User).filter(User.id == u.id).delete()
            db.commit()
            db.close()

    def test_47_get_topics_endpoint_filtering(self):
        db = SessionLocal()
        try:
            u = User(platform_id=1, username="c85_api_topic_user_filter", display_name="Filter API User")
            db.add(u)
            db.commit()

            t1 = datetime(2026, 1, 1, 10, 0, 0)
            t2 = datetime(2026, 1, 2, 10, 0, 0)

            p1 = Post(
                platform_id=1,
                user_id=u.id,
                external_post_id="c85_api_flt_p1",
                text="Python machine learning post",
                posted_at=t1,
                collected_at=t1,
                language="en",
            )
            p2 = Post(
                platform_id=1,
                user_id=u.id,
                external_post_id="c85_api_flt_p2",
                text="Football champions league match",
                posted_at=t2,
                collected_at=t2,
                language="te",
            )
            db.add_all([p1, p2])
            db.commit()

            topic1 = Topic(name="topic_api_filter_python")
            topic2 = Topic(name="topic_api_filter_sports")
            db.add_all([topic1, topic2])
            db.commit()

            pt1 = PostTopic(post_id=p1.id, topic_id=topic1.id)
            pt2 = PostTopic(post_id=p2.id, topic_id=topic2.id)
            db.add_all([pt1, pt2])
            db.commit()

            code_lang, data_lang = call_api("GET", "/api/v1/analytics/topics?language=en")
            self.assertEqual(code_lang, 200)
            names_lang = [item["topic_name"] for item in data_lang["items"]]
            self.assertIn("topic_api_filter_python", names_lang)
            self.assertNotIn("topic_api_filter_sports", names_lang)

            code_srch, data_srch = call_api("GET", "/api/v1/analytics/topics?search=football")
            self.assertEqual(code_srch, 200)
            names_srch = [item["topic_name"] for item in data_srch["items"]]
            self.assertIn("topic_api_filter_sports", names_srch)
            self.assertNotIn("topic_api_filter_python", names_srch)
        finally:
            db.query(PostTopic).filter(PostTopic.post_id.in_([p1.id, p2.id])).delete(synchronize_session=False)
            db.query(Post).filter(Post.id.in_([p1.id, p2.id])).delete(synchronize_session=False)
            db.query(Topic).filter(Topic.id.in_([topic1.id, topic2.id])).delete(synchronize_session=False)
            db.query(User).filter(User.id == u.id).delete()
            db.commit()
            db.close()

    def test_48_get_topics_endpoint_sorting_and_pagination(self):
        db = SessionLocal()
        try:
            u = User(platform_id=1, username="c85_api_topic_user_sort", display_name="Sort API User")
            db.add(u)
            db.commit()

            t1 = datetime(2026, 1, 1, 10, 0, 0)
            t2 = datetime(2026, 1, 2, 10, 0, 0)

            p1 = Post(
                platform_id=1,
                user_id=u.id,
                external_post_id="c85_api_sort_p1",
                text="Topic sorting post low",
                posted_at=t1,
                collected_at=t1,
                language="en",
            )
            p2 = Post(
                platform_id=1,
                user_id=u.id,
                external_post_id="c85_api_sort_p2",
                text="Topic sorting post high",
                posted_at=t2,
                collected_at=t2,
                language="en",
            )
            db.add_all([p1, p2])
            db.commit()

            topic1 = Topic(name="topic_api_sort_low")
            topic2 = Topic(name="topic_api_sort_high")
            db.add_all([topic1, topic2])
            db.commit()

            pt1 = PostTopic(post_id=p1.id, topic_id=topic1.id)
            pt2 = PostTopic(post_id=p2.id, topic_id=topic2.id)
            db.add_all([pt1, pt2])
            db.commit()

            m1 = PostMetric(post_id=p1.id, collected_at=t1, likes=50, comments=0, shares=0, views=0)
            m2 = PostMetric(post_id=p2.id, collected_at=t2, likes=500, comments=0, shares=0, views=0)
            db.add_all([m1, m2])
            db.commit()

            code, data = call_api("GET", "/api/v1/analytics/topics?sort_by=total_likes&order=desc")
            self.assertEqual(code, 200)
            topic_names = [item["topic_name"] for item in data["items"]]
            idx_high = topic_names.index("topic_api_sort_high")
            idx_low = topic_names.index("topic_api_sort_low")
            self.assertLess(idx_high, idx_low)

            code_p1, data_p1 = call_api("GET", "/api/v1/analytics/topics?search=Topic+sorting+post&sort_by=total_likes&order=desc&limit=1&offset=0")
            self.assertEqual(code_p1, 200)
            self.assertEqual(data_p1["limit"], 1)
            self.assertEqual(data_p1["offset"], 0)
            self.assertEqual(len(data_p1["items"]), 1)
            self.assertEqual(data_p1["items"][0]["topic_name"], "topic_api_sort_high")

            code_p2, data_p2 = call_api("GET", "/api/v1/analytics/topics?search=Topic+sorting+post&sort_by=total_likes&order=desc&limit=1&offset=1")
            self.assertEqual(code_p2, 200)
            self.assertEqual(data_p2["limit"], 1)
            self.assertEqual(data_p2["offset"], 1)
            self.assertEqual(len(data_p2["items"]), 1)
            self.assertEqual(data_p2["items"][0]["topic_name"], "topic_api_sort_low")
        finally:
            db.query(PostMetric).filter(PostMetric.post_id.in_([p1.id, p2.id])).delete(synchronize_session=False)
            db.query(PostTopic).filter(PostTopic.post_id.in_([p1.id, p2.id])).delete(synchronize_session=False)
            db.query(Post).filter(Post.id.in_([p1.id, p2.id])).delete(synchronize_session=False)
            db.query(Topic).filter(Topic.id.in_([topic1.id, topic2.id])).delete(synchronize_session=False)
            db.query(User).filter(User.id == u.id).delete()
            db.commit()
            db.close()

    def test_49_get_topics_endpoint_validation_errors(self):
        code_sort, data_sort = call_api("GET", "/api/v1/analytics/topics?sort_by=unsupported_col")
        self.assertEqual(code_sort, 400)
        self.assertIn("Invalid sort_by", data_sort.get("detail", ""))

        code_ord, data_ord = call_api("GET", "/api/v1/analytics/topics?order=sideways")
        self.assertEqual(code_ord, 400)
        self.assertIn("Invalid order", data_ord.get("detail", ""))

        code_date, data_date = call_api("GET", "/api/v1/analytics/topics?start_date=2026-12-01T00:00:00&end_date=2026-01-01T00:00:00")
        self.assertEqual(code_date, 400)
        self.assertIn("start_date cannot be after end_date", data_date.get("detail", ""))

        code_lim, _ = call_api("GET", "/api/v1/analytics/topics?limit=0")
        self.assertEqual(code_lim, 422)

        code_lim2, _ = call_api("GET", "/api/v1/analytics/topics?limit=201")
        self.assertEqual(code_lim2, 422)

        code_off, _ = call_api("GET", "/api/v1/analytics/topics?offset=-1")
        self.assertEqual(code_off, 422)

    # --- Component 8.6: Engagement Time-Series Aggregation API tests ---

    def test_50_get_engagement_timeseries_endpoint_basic(self):
        code, data = call_api("GET", "/api/v1/analytics/timeseries/engagement")
        self.assertEqual(code, 200)
        self.assertEqual(data.get("interval"), "day")
        self.assertIn("total_points", data)
        self.assertIn("points", data)
        if data["points"]:
            first = data["points"][0]
            self.assertIn("date", first)
            self.assertIn("post_count", first)
            self.assertIn("total_likes", first)
            self.assertIn("total_comments", first)
            self.assertIn("total_shares", first)
            self.assertIn("total_views", first)
            self.assertIn("avg_likes", first)

    def test_51_get_engagement_timeseries_endpoint_filtering(self):
        code, data = call_api("GET", "/api/v1/analytics/timeseries/engagement?language=en&search=infrastructure")
        self.assertEqual(code, 200)
        self.assertEqual(data.get("interval"), "day")
        self.assertIn("total_points", data)
        self.assertIn("points", data)

    def test_52_get_engagement_timeseries_endpoint_invalid_date_range_400(self):
        code, data = call_api("GET", "/api/v1/analytics/timeseries/engagement?start_date=2026-12-01T00:00:00&end_date=2026-01-01T00:00:00")
        self.assertEqual(code, 400)
        self.assertIn("start_date cannot be after end_date", data.get("detail", ""))

    # --- Component 9: API Hardening Tests ---

    def test_53_count_endpoint_invalid_date_range_400(self):
        code, data = call_api("GET", "/api/v1/analytics/count?start_date=2026-12-01T00:00:00&end_date=2026-01-01T00:00:00")
        self.assertEqual(code, 400)
        self.assertIn("start_date cannot be after end_date", data.get("detail", ""))

    def test_54_engagement_endpoint_invalid_date_range_400(self):
        code, data = call_api("GET", "/api/v1/analytics/engagement?start_date=2026-12-01T00:00:00&end_date=2026-01-01T00:00:00")
        self.assertEqual(code, 400)
        self.assertIn("start_date cannot be after end_date", data.get("detail", ""))

    def test_55_timeseries_endpoint_invalid_date_range_400(self):
        code, data = call_api("GET", "/api/v1/analytics/timeseries?start_date=2026-12-01T00:00:00&end_date=2026-01-01T00:00:00")
        self.assertEqual(code, 400)
        self.assertIn("start_date cannot be after end_date", data.get("detail", ""))

    def test_56_unified_sort_validator_consistency(self):
        # Posts sort_by / order
        code, data = call_api("GET", "/api/v1/analytics/posts?sort_by=nonexistent_field")
        self.assertEqual(code, 400)
        self.assertIn("Invalid sort_by", data.get("detail", ""))

        code, data = call_api("GET", "/api/v1/analytics/posts?order=invalid_dir")
        self.assertEqual(code, 400)
        self.assertIn("Invalid order", data.get("detail", ""))

        # Authors sort_by / order
        code, data = call_api("GET", "/api/v1/analytics/authors?sort_by=nonexistent_field")
        self.assertEqual(code, 400)
        self.assertIn("Invalid sort_by", data.get("detail", ""))

        code, data = call_api("GET", "/api/v1/analytics/authors?order=invalid_dir")
        self.assertEqual(code, 400)
        self.assertIn("Invalid order", data.get("detail", ""))

        # Topics sort_by / order
        code, data = call_api("GET", "/api/v1/analytics/topics?sort_by=nonexistent_field")
        self.assertEqual(code, 400)
        self.assertIn("Invalid sort_by", data.get("detail", ""))

        code, data = call_api("GET", "/api/v1/analytics/topics?order=invalid_dir")
        self.assertEqual(code, 400)
        self.assertIn("Invalid order", data.get("detail", ""))


if __name__ == "__main__":
    unittest.main()
