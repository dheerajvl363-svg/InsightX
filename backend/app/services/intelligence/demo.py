import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.schemas.data_quality import AnalyticsReadyPost
from app.schemas.intelligence import (
    DemoAnalysisResponse,
    DemoAnalyzePostsRequest,
    DemoContextMode,
    DemoPostInput,
    DemoProvenance,
    InsightExplanation,
    InsightItem,
)
from app.schemas.post import NormalizedPost, RawPostPayload
from app.services.data_quality import DataQualityService
from app.services.ingestion import IngestionService
from app.services.intelligence.ai.service import (
    AIAssistedIntelligenceService,
    get_ai_intelligence_service,
)
from app.services.intelligence.workflow import (
    UnifiedIntelligenceWorkflow,
    get_unified_workflow,
)
from app.services.normalizer import DataNormalizer

logger = logging.getLogger(__name__)

MOCK_DATA_FILENAME = "mock_posts.json"


def get_mock_data_path() -> Path:
    """Resolves the path to the canonical mock posts dataset."""
    backend_dir = Path(__file__).resolve().parents[3]
    candidate = backend_dir / "data" / MOCK_DATA_FILENAME
    if candidate.exists():
        return candidate

    alt_candidate = Path("backend/data") / MOCK_DATA_FILENAME
    if alt_candidate.exists():
        return alt_candidate.resolve()

    alt_candidate2 = Path("data") / MOCK_DATA_FILENAME
    if alt_candidate2.exists():
        return alt_candidate2.resolve()

    return candidate


class DemoIntelligenceService:
    """
    Orchestrates the single-post and multi-post demo analysis pipeline.
    Connects:
      User-supplied posts (1 to 50)
      → Platform Normalization & Provenance Tagging ('user_supplied')
      → Optional Database Persistence via IngestionService
      → Background Context Assembly ('sample_stream', 'database', 'none')
      → Unified Intelligence Workflow (Sentiment, Topics, Trends, Network)
      → Deterministic Insights & Auditable Explanations
      → Optional Evidence-Grounded AI Interpretation
      → DemoAnalysisResponse
    """

    def __init__(
        self,
        workflow: Optional[UnifiedIntelligenceWorkflow] = None,
        quality_service: Optional[DataQualityService] = None,
        ai_service: Optional[AIAssistedIntelligenceService] = None,
        db: Optional[Session] = None,
    ):
        self.db = db
        self.workflow = workflow or get_unified_workflow(db=db)
        self.quality_service = quality_service or DataQualityService()
        self.ai_service = ai_service or get_ai_intelligence_service()

    def load_sample_context(self) -> Tuple[List[AnalyticsReadyPost], List[str]]:
        """
        Loads the established mock dataset as sample background context.
        Strictly tags all loaded records as 'sample_context' to ensure zero fabrication.
        """
        warnings: List[str] = []
        path = get_mock_data_path()
        if not path.exists():
            warnings.append(f"Sample context dataset not found at {path}. Proceeding without sample context.")
            return [], warnings

        try:
            with open(path, "r", encoding="utf-8") as f:
                raw_records = json.load(f)
        except Exception as e:
            logger.error(f"Failed to read mock data file: {e}")
            warnings.append(f"Failed to load sample dataset: {e}")
            return [], warnings

        normalized_posts: List[NormalizedPost] = []
        for r in raw_records:
            try:
                raw_payload = RawPostPayload.model_validate(r)
                norm = DataNormalizer.normalize(raw_payload)
                norm.metadata["provenance"] = DemoProvenance.SAMPLE_CONTEXT.value
                norm.metadata["is_user_seed"] = False
                normalized_posts.append(norm)
            except Exception as ex:
                logger.debug(f"Skipping malformed sample record: {ex}")

        batch_result = self.quality_service.validate_batch(normalized_posts)
        return batch_result.valid_posts, warnings

    def load_database_context(
        self,
        limit: int = 100,
    ) -> Tuple[List[AnalyticsReadyPost], List[str]]:
        """
        Loads recent posts from the database to serve as background comparison context.
        Strictly tags all loaded records as 'database_context'.
        """
        warnings: List[str] = []
        if self.db is None:
            warnings.append("Database context requested, but no active database session is available.")
            return [], warnings

        try:
            from app.api.routes.analytics import _fetch_db_posts_as_analytics_ready

            db_posts = _fetch_db_posts_as_analytics_ready(db=self.db, limit=limit)
            for p in db_posts:
                p.metadata["provenance"] = DemoProvenance.DATABASE_CONTEXT.value
                p.metadata["is_user_seed"] = False

            if not db_posts:
                warnings.append("Database context is currently empty (0 posts found). Analyzed against user posts only.")

            return db_posts, warnings
        except Exception as e:
            logger.error(f"Error loading database context: {e}")
            warnings.append(f"Failed to load database context: {e}")
            return [], warnings

    def process_user_posts(
        self,
        posts: List[DemoPostInput],
        persist_to_db: bool = True,
    ) -> Tuple[List[AnalyticsReadyPost], List[Dict[str, Any]], bool, List[str]]:
        """
        Transforms user-supplied demo inputs into validated AnalyticsReadyPost records.
        Applies platform normalization, injects 'user_supplied' provenance,
        and optionally persists to PostgreSQL using the existing IngestionService.
        """
        warnings: List[str] = []
        valid_user_posts: List[AnalyticsReadyPost] = []
        seed_posts_meta: List[Dict[str, Any]] = []
        persisted_any = False

        ingestion_service: Optional[IngestionService] = None
        if persist_to_db:
            if self.db is not None:
                try:
                    ingestion_service = IngestionService(self.db)
                except Exception as e:
                    warnings.append(f"Database persistence unavailable: {e}. Running in-memory.")
            else:
                warnings.append("Persistence requested, but database session is not connected. Running in-memory.")

        for post_input in posts:
            raw_payload = post_input.to_raw_post_payload()
            norm = DataNormalizer.normalize(raw_payload)

            # Ensure provenance is strictly user_supplied
            norm.metadata["provenance"] = DemoProvenance.USER_SUPPLIED.value
            norm.metadata["is_user_seed"] = True

            db_post_id: Optional[int] = None
            if ingestion_service is not None:
                try:
                    ingest_res = ingestion_service.ingest_post(norm, auto_commit=True)
                    if ingest_res.status in ("success", "duplicate_ignored"):
                        db_post_id = ingest_res.post_id
                        persisted_any = True
                        norm.metadata["db_id"] = db_post_id
                except Exception as e:
                    logger.warning(f"Failed to persist post {norm.external_post_id}: {e}")
                    warnings.append(f"Persistence error for {norm.external_post_id}: {e}")

            val_res = self.quality_service.validate_and_prepare(norm)
            if val_res.is_valid and val_res.post:
                ready_post = val_res.post
                if db_post_id is not None:
                    ready_post.id = db_post_id
                    ready_post.metadata["db_id"] = db_post_id

                ready_post.metadata["provenance"] = DemoProvenance.USER_SUPPLIED.value
                ready_post.metadata["is_user_seed"] = True

                valid_user_posts.append(ready_post)

                seed_meta = {
                    "platform": ready_post.platform,
                    "external_post_id": ready_post.external_post_id,
                    "text": ready_post.text,
                    "author_username": ready_post.author_username,
                    "author_display_name": ready_post.author_display_name,
                    "posted_at": ready_post.posted_at.isoformat(),
                    "url": ready_post.url,
                    "metrics": ready_post.metrics.model_dump() if ready_post.metrics else {},
                    "provenance": DemoProvenance.USER_SUPPLIED.value,
                    "is_user_seed": True,
                    "db_id": db_post_id,
                    "char_count": ready_post.char_count,
                    "word_count": ready_post.word_count,
                }
                seed_posts_meta.append(seed_meta)
            else:
                warnings.append(f"Post '{post_input.text[:30]}...' quality notice: {', '.join(val_res.errors or val_res.warnings)}")
                # If validation failed on an edge case, still keep the post in fallback ready format if possible
                if val_res.post:
                    valid_user_posts.append(val_res.post)

        return valid_user_posts, seed_posts_meta, persisted_any, warnings

    def analyze_demo_posts(
        self,
        request: DemoAnalyzePostsRequest,
    ) -> DemoAnalysisResponse:
        """
        Executes end-to-end demo analysis across user-supplied posts (1 to 50)
        and contextual baseline data.
        """
        all_warnings: List[str] = []

        # 1. Process user-supplied posts
        user_posts, seed_posts, persisted, user_warnings = self.process_user_posts(
            posts=request.posts,
            persist_to_db=request.persist_to_db,
        )
        all_warnings.extend(user_warnings)

        if not user_posts:
            raise ValueError("All user-supplied posts failed data quality validation.")

        # 2. Assemble context posts according to requested mode
        context_posts: List[AnalyticsReadyPost] = []
        if request.context_mode == DemoContextMode.SAMPLE_STREAM:
            sample_posts, sample_warnings = self.load_sample_context()
            context_posts.extend(sample_posts)
            all_warnings.extend(sample_warnings)
        elif request.context_mode == DemoContextMode.DATABASE:
            db_posts, db_warnings = self.load_database_context(limit=100)
            context_posts.extend(db_posts)
            all_warnings.extend(db_warnings)
        elif request.context_mode == DemoContextMode.NONE:
            # Explicitly analyze only user posts with zero contextual expansion
            context_posts = []

        # 3. Combine user posts + context posts for unified analysis
        total_eval_posts = list(user_posts) + list(context_posts)

        # 4. Run Unified Intelligence Workflow
        unified_report = self.workflow.run_workflow(
            posts=total_eval_posts,
            generate_explanations=True,
            include_ai=request.include_ai,
        )

        # 5. Resolve Primary Insight grounded in user posts
        primary_insight: Optional[InsightItem] = None
        ambient_insight: Optional[InsightItem] = None
        is_seed_grounded = False

        user_ext_ids = {p.external_post_id for p in user_posts if p.external_post_id}
        user_db_ids = {p.id for p in user_posts if p.id is not None}

        # Check for insight whose evidence directly references any user post
        for ins in unified_report.batch_insights.insights:
            ev = ins.evidence
            matched_ext = any(ext in user_ext_ids for ext in (ev.external_post_ids or []))
            matched_id = any(pid in user_db_ids for pid in (ev.post_ids or []))
            if matched_ext or matched_id:
                primary_insight = ins
                is_seed_grounded = True
                break

        # Capture top ambient context insight if any exist and no seed insight was found
        if not is_seed_grounded and unified_report.batch_insights.insights:
            ambient_insight = unified_report.batch_insights.insights[0]

        # 6. Resolve Primary AI Qualitative Interpretation if requested
        primary_ai_interpretation: Optional[Any] = None
        # Only synthesize AI interpretation if there is a genuine seed-grounded primary insight
        if request.include_ai and primary_insight and is_seed_grounded:
            matching_expl: Optional[InsightExplanation] = None
            for expl in unified_report.explanations:
                if expl.insight_id == primary_insight.id:
                    matching_expl = expl
                    break

            try:
                ai_res = self.ai_service.analyze_insight(
                    insight=primary_insight,
                    explanation=matching_expl,
                    prompt_instructions=request.prompt_instructions,
                )
                primary_ai_interpretation = ai_res.model_dump() if hasattr(ai_res, "model_dump") else ai_res
            except Exception as ai_err:
                logger.warning(f"AI interpretation failed for primary insight: {ai_err}")
                all_warnings.append(f"AI qualitative interpretation unavailable: {ai_err}. Deterministic insights remain valid.")

        return DemoAnalysisResponse(
            seed_posts=seed_posts,
            provenance=DemoProvenance.USER_SUPPLIED,
            user_post_count=len(user_posts),
            context_post_count=len(context_posts),
            total_context_size=len(total_eval_posts),
            context_mode=request.context_mode,
            persisted=persisted,
            unified_report=unified_report,
            is_seed_grounded=is_seed_grounded,
            primary_insight=primary_insight,
            ambient_insight=ambient_insight,
            primary_ai_interpretation=primary_ai_interpretation,
            warnings=all_warnings,
            executed_at=datetime.now(timezone.utc),
        )


def get_demo_intelligence_service(
    db: Optional[Session] = None,
) -> DemoIntelligenceService:
    """Factory creating a DemoIntelligenceService instance."""
    return DemoIntelligenceService(
        workflow=get_unified_workflow(db=db),
        quality_service=DataQualityService(),
        ai_service=get_ai_intelligence_service(),
        db=db,
    )
