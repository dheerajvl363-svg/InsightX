import pytest
from unittest.mock import MagicMock

from app.schemas.intelligence import (
    DemoAnalyzePostsRequest,
    DemoContextMode,
    DemoPostInput,
    DemoProvenance,
)
from app.services.intelligence.demo import DemoIntelligenceService
from app.services.intelligence.ai import MockAIProvider, AIAssistedIntelligenceService


@pytest.fixture
def mock_ai_service():
    provider = MockAIProvider()
    return AIAssistedIntelligenceService(provider=provider)


@pytest.fixture
def demo_service(mock_ai_service):
    return DemoIntelligenceService(
        ai_service=mock_ai_service,
        db=None,
    )


def test_single_post_analysis_sample_context(demo_service):
    """Test analyzing a single user post with sample context enabled.
    Phase 9.10: Single post below volume threshold must have is_seed_grounded=False
    and primary_insight=None (no fake seed trend), while ambient_insight captures background context.
    """
    user_post = DemoPostInput(
        text="Critical cybersecurity alert: Major outage detected across cloud infrastructure. #outage",
        author="@sec_lead",
        likes=150,
        comments=45,
        shares=80,
    )
    request = DemoAnalyzePostsRequest(
        posts=[user_post],
        context_mode=DemoContextMode.SAMPLE_STREAM,
        persist_to_db=False,
        include_ai=True,
    )

    response = demo_service.analyze_demo_posts(request)

    assert response.user_post_count == 1
    assert response.context_post_count > 0
    assert response.total_context_size == response.user_post_count + response.context_post_count
    assert response.context_mode == DemoContextMode.SAMPLE_STREAM
    assert response.persisted is False

    # Check user seed post details
    assert len(response.seed_posts) == 1
    seed = response.seed_posts[0]
    assert seed["provenance"] == DemoProvenance.USER_SUPPLIED.value
    assert seed["is_user_seed"] is True
    assert seed["author_username"] == "sec_lead"
    assert "outage" in seed["text"].lower()

    # Check deterministic unified report is populated
    assert response.unified_report is not None
    assert response.unified_report.analytics_summary["total_posts"] == response.total_context_size

    # Phase 9.10: Single post does not meet threshold for seed trend
    assert response.is_seed_grounded is False
    assert response.primary_insight is None
    # Ambient baseline insight is preserved separately without seed mislabeling
    assert response.ambient_insight is not None
    assert response.primary_ai_interpretation is None


def test_multi_post_analysis_seed_grounded(demo_service):
    """Phase 9.10: Multiple related posts trigger genuine seed-grounded insight with AI interpretation."""
    posts = [
        DemoPostInput(text="Payment gateway cluster 1 failing transactions across all users.", author="user_a"),
        DemoPostInput(text="Payment gateway cluster 2 timeout errors spiking rapidly.", author="user_b"),
        DemoPostInput(text="Payment gateway outage confirmed by merchant services.", author="user_c"),
    ]
    request = DemoAnalyzePostsRequest(
        posts=posts,
        context_mode=DemoContextMode.SAMPLE_STREAM,
        persist_to_db=False,
        include_ai=True,
    )

    response = demo_service.analyze_demo_posts(request)

    assert response.user_post_count == 3
    assert response.is_seed_grounded is True
    assert response.primary_insight is not None
    assert "Payment" in response.primary_insight.title or "Outage" in response.primary_insight.title
    assert response.primary_ai_interpretation is not None
    # Evidence must link to user seed external IDs
    seed_ext_ids = {p.get("external_post_id") for p in response.seed_posts}
    evidence_ext_ids = set(response.primary_insight.evidence.external_post_ids or [])
    assert bool(seed_ext_ids.intersection(evidence_ext_ids))


def test_multi_post_analysis_none_context(demo_service):
    """Test analyzing multiple posts with no background context (context_mode='none')."""
    posts = [
        DemoPostInput(
            text=f"Update {i}: Monitoring server latency and database connection pool health.",
            author=f"devops_{i}",
            likes=10 * i,
        )
        for i in range(1, 6)
    ]
    request = DemoAnalyzePostsRequest(
        posts=posts,
        context_mode=DemoContextMode.NONE,
        persist_to_db=False,
        include_ai=False,
    )

    response = demo_service.analyze_demo_posts(request)

    assert response.user_post_count == 5
    assert response.context_post_count == 0
    assert response.total_context_size == 5
    assert response.context_mode == DemoContextMode.NONE
    assert len(response.seed_posts) == 5

    for seed in response.seed_posts:
        assert seed["provenance"] == DemoProvenance.USER_SUPPLIED.value
        assert seed["is_user_seed"] is True

    assert response.unified_report.analytics_summary["total_posts"] == 5
    assert response.primary_ai_interpretation is None


def test_demo_service_handles_ai_failure_gracefully(demo_service):
    """Test that if AI service raises an error on a seed-grounded insight, deterministic analysis succeeds with a warning."""
    failing_ai_service = MagicMock(spec=AIAssistedIntelligenceService)
    failing_ai_service.analyze_insight.side_effect = RuntimeError("Provider timeout simulation")

    service = DemoIntelligenceService(
        ai_service=failing_ai_service,
        db=None,
    )

    request = DemoAnalyzePostsRequest(
        posts=[
            DemoPostInput(text="Payment gateway failure alert 1.", author="op1"),
            DemoPostInput(text="Payment gateway failure alert 2.", author="op2"),
            DemoPostInput(text="Payment gateway failure alert 3.", author="op3"),
        ],
        context_mode=DemoContextMode.SAMPLE_STREAM,
        persist_to_db=False,
        include_ai=True,
    )

    response = service.analyze_demo_posts(request)

    assert response.user_post_count == 3
    assert response.is_seed_grounded is True
    assert response.primary_insight is not None
    assert response.unified_report is not None
    assert response.primary_ai_interpretation is None
    assert any("AI qualitative interpretation unavailable" in w for w in response.warnings)


def test_persistence_fallback_when_no_db(demo_service):
    """Test graceful handling and warning when persist_to_db is True but db is None."""
    request = DemoAnalyzePostsRequest(
        posts=[
            DemoPostInput(
                text="Local testing post without connected SQL database session.",
                author="offline_tester",
            )
        ],
        context_mode=DemoContextMode.NONE,
        persist_to_db=True,
        include_ai=False,
    )

    response = demo_service.analyze_demo_posts(request)

    assert response.persisted is False
    assert any("Persistence requested, but database session is not connected" in w for w in response.warnings)


def test_persistence_with_mocked_ingestion(mock_ai_service):
    """Test persistence logic when IngestionService successfully ingests posts."""
    mock_db = MagicMock()
    service = DemoIntelligenceService(
        ai_service=mock_ai_service,
        db=mock_db,
    )

    from unittest.mock import patch
    from app.schemas.post import IngestionResponse
    from datetime import datetime, timezone

    fake_ingest_response = IngestionResponse(
        status="success",
        post_id=42,
        external_post_id="demo_post_test",
        platform="X",
        is_duplicate=False,
        message="Post successfully ingested.",
        collected_at=datetime.now(timezone.utc),
    )

    with patch("app.services.intelligence.demo.IngestionService") as mock_ingest_cls:
        mock_ingest_instance = MagicMock()
        mock_ingest_instance.ingest_post.return_value = fake_ingest_response
        mock_ingest_cls.return_value = mock_ingest_instance

        request = DemoAnalyzePostsRequest(
            posts=[
                DemoPostInput(
                    text="Testing persistence flow with mocked ingestion engine.",
                    author="persist_tester",
                )
            ],
            context_mode=DemoContextMode.NONE,
            persist_to_db=True,
            include_ai=False,
        )

        response = service.analyze_demo_posts(request)

        assert response.persisted is True
        assert len(response.seed_posts) == 1
        assert response.seed_posts[0]["db_id"] == 42
        mock_ingest_instance.ingest_post.assert_called_once()


def test_database_context_mode(mock_ai_service):
    """Test assembling context from database mode."""
    mock_db = MagicMock()
    service = DemoIntelligenceService(
        ai_service=mock_ai_service,
        db=mock_db,
    )

    from unittest.mock import patch
    from app.schemas.data_quality import AnalyticsReadyPost
    from datetime import datetime, timezone

    fake_db_post = AnalyticsReadyPost(
        id=101,
        platform="X",
        external_post_id="db_seed_1",
        text="Historical background record from database context.",
        posted_at=datetime.now(timezone.utc),
        metadata={},
        char_count=50,
        word_count=7,
    )

    with patch("app.api.routes.analytics._fetch_db_posts_as_analytics_ready", return_value=[fake_db_post]):
        request = DemoAnalyzePostsRequest(
            posts=[
                DemoPostInput(
                    text="Fresh incoming tweet to evaluate against DB context.",
                    author="analyst",
                )
            ],
            context_mode=DemoContextMode.DATABASE,
            persist_to_db=False,
            include_ai=False,
        )

        response = service.analyze_demo_posts(request)

        assert response.user_post_count == 1
        assert response.context_post_count == 1
        assert response.total_context_size == 2
        assert response.context_mode == DemoContextMode.DATABASE

