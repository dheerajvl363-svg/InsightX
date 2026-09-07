from datetime import datetime, timezone
import logging
from typing import List, Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.metric import PostMetric
from app.models.platform import Platform
from app.models.post import Post
from app.models.user import User
from app.schemas.post import (
    BatchIngestionResponse,
    IngestionResponse,
    NormalizedPost,
)

logger = logging.getLogger(__name__)


class IngestionService:
    """
    Service responsible for persisting normalized social media posts into PostgreSQL.
    Handles platform resolution, author deduplication, idempotent post insertion,
    metric time-series snapshot storage, and transactional safety.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_or_create_platform(self, name: str) -> Platform:
        """
        Finds an existing platform by canonical name or registers it.
        """
        if not name or not name.strip():
            raise ValueError("Platform name cannot be empty.")

        platform = self.db.query(Platform).filter(Platform.name == name.strip()).first()
        if not platform:
            logger.info(f"Registering new platform: {name.strip()}")
            platform = Platform(name=name.strip())
            self.db.add(platform)
            self.db.flush()
        return platform

    def get_or_create_user(
        self,
        platform_id: int,
        username: Optional[str],
        display_name: Optional[str] = None,
    ) -> Optional[User]:
        """
        Resolves or creates a user associated with a given platform.
        Returns None if username is empty or not provided.
        """
        if not username or not username.strip():
            return None

        clean_username = username.strip()
        user = (
            self.db.query(User)
            .filter(
                User.platform_id == platform_id,
                User.username == clean_username,
            )
            .first()
        )

        if not user:
            user = User(
                platform_id=platform_id,
                username=clean_username,
                display_name=display_name.strip() if display_name else None,
                created_at=datetime.now(timezone.utc),
            )
            self.db.add(user)
            self.db.flush()
        elif display_name and not user.display_name:
            user.display_name = display_name.strip()
            self.db.flush()

        return user

    def ingest_post(self, post_data: NormalizedPost, auto_commit: bool = True) -> IngestionResponse:
        """
        Ingests a single NormalizedPost into PostgreSQL.
        Handles platform resolution, author resolution, deduplication, metrics, and rollback on error.
        """
        try:
            # 1. Resolve Platform
            platform = self.get_or_create_platform(post_data.platform_name)

            # 2. Resolve Author User (nullable)
            user = self.get_or_create_user(
                platform_id=platform.id,
                username=post_data.author_username,
                display_name=post_data.author_display_name,
            )
            user_id = user.id if user else None

            # 3. Deduplication check by (platform_id, external_post_id)
            existing_post = (
                self.db.query(Post)
                .filter(
                    Post.platform_id == platform.id,
                    Post.external_post_id == post_data.external_post_id,
                )
                .first()
            )

            if existing_post:
                logger.debug(
                    f"Duplicate post detected: platform={platform.name}, external_id={post_data.external_post_id}"
                )
                # If new metrics are supplied, record an updated metric snapshot
                if post_data.metrics:
                    metric = PostMetric(
                        post_id=existing_post.id,
                        collected_at=post_data.collected_at,
                        likes=post_data.metrics.likes,
                        comments=post_data.metrics.comments,
                        shares=post_data.metrics.shares,
                        views=post_data.metrics.views,
                    )
                    self.db.add(metric)

                if auto_commit:
                    self.db.commit()

                return IngestionResponse(
                    status="duplicate_ignored",
                    post_id=existing_post.id,
                    external_post_id=post_data.external_post_id,
                    platform=platform.name,
                    is_duplicate=True,
                    message="Post already exists. Duplicate ignored; metrics updated if provided.",
                    collected_at=post_data.collected_at,
                )

            # 4. Create new Post record
            new_post = Post(
                platform_id=platform.id,
                user_id=user_id,
                external_post_id=post_data.external_post_id,
                text=post_data.text,
                posted_at=post_data.posted_at,
                collected_at=post_data.collected_at,
                url=post_data.url,
                language=post_data.language,
                metadata_=post_data.metadata or {},
                raw_payload=post_data.raw_payload or {},
            )
            self.db.add(new_post)
            self.db.flush()

            # 5. Persist engagement metrics if provided
            if post_data.metrics:
                metric = PostMetric(
                    post_id=new_post.id,
                    collected_at=post_data.collected_at,
                    likes=post_data.metrics.likes,
                    comments=post_data.metrics.comments,
                    shares=post_data.metrics.shares,
                    views=post_data.metrics.views,
                )
                self.db.add(metric)

            if auto_commit:
                self.db.commit()

            return IngestionResponse(
                status="success",
                post_id=new_post.id,
                external_post_id=new_post.external_post_id,
                platform=platform.name,
                is_duplicate=False,
                message="Post successfully ingested.",
                collected_at=new_post.collected_at,
            )

        except Exception as exc:
            if auto_commit:
                self.db.rollback()
            logger.error(
                f"Error ingesting post {post_data.external_post_id}: {exc}",
                exc_info=True,
            )
            raise

    def ingest_batch(self, posts: List[NormalizedPost]) -> BatchIngestionResponse:
        """
        Ingests a batch of NormalizedPost records using nested savepoints.
        A failure in one post will not abort or corrupt the rest of the batch.
        """
        results: List[IngestionResponse] = []
        successful = 0
        duplicates = 0
        failed = 0

        for post_data in posts:
            savepoint = self.db.begin_nested()
            try:
                resp = self.ingest_post(post_data, auto_commit=False)
                savepoint.commit()
                results.append(resp)
                if resp.is_duplicate:
                    duplicates += 1
                else:
                    successful += 1
            except Exception as exc:
                savepoint.rollback()
                logger.error(
                    f"Failed batch post {post_data.external_post_id}: {exc}",
                    exc_info=True,
                )
                failed += 1
                results.append(
                    IngestionResponse(
                        status="failed",
                        post_id=None,
                        external_post_id=post_data.external_post_id,
                        platform=post_data.platform_name,
                        is_duplicate=False,
                        message=f"Ingestion failed: {str(exc)}",
                        collected_at=post_data.collected_at,
                    )
                )

        self.db.commit()

        return BatchIngestionResponse(
            total_received=len(posts),
            successful=successful,
            duplicates=duplicates,
            failed=failed,
            results=results,
        )
