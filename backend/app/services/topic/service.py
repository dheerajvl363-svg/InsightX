from datetime import datetime, timezone
from typing import List, Optional

from app.schemas.data_quality import AnalyticsReadyPost
from app.schemas.topic import (
    BatchTopicResult,
    ExtractedTopic,
    SinglePostTopicResult,
)
from app.services.topic.base import BaseTopicEngine
from app.services.topic.engine import RuleBasedTopicEngine


class TopicAnalysisService:
    """
    Topic Analysis and Narrative Detection Service for Phase 3.
    Extracts keywords, phrases, and hashtags from AnalyticsReadyPost instances,
    and clusters collections of posts into cohesive topic groups.
    """

    def __init__(self, engine: Optional[BaseTopicEngine] = None):
        self.engine = engine or RuleBasedTopicEngine()

    def extract_post_topics(self, post: AnalyticsReadyPost) -> SinglePostTopicResult:
        """
        Extracts keywords, keyphrases, and candidate topic label for a single post.
        """
        if not isinstance(post, AnalyticsReadyPost):
            raise TypeError(f"Expected AnalyticsReadyPost, got {type(post).__name__}")

        return self.engine.extract_post_topics(post)

    def extract_topics(self, posts: List[AnalyticsReadyPost]) -> BatchTopicResult:
        """
        Extracts multi-post topic clusters across a collection of posts.
        """
        if not posts:
            return BatchTopicResult(
                total_posts_analyzed=0,
                total_topics_found=0,
                topics=[],
                unclustered_posts_count=0,
                model=self.engine.model_name,
                analyzed_at=datetime.now(timezone.utc),
            )

        for p in posts:
            if not isinstance(p, AnalyticsReadyPost):
                raise TypeError(f"Expected list of AnalyticsReadyPost, found {type(p).__name__}")

        extracted_topics: List[ExtractedTopic] = self.engine.extract_batch_topics(posts)

        clustered_post_count = sum(t.post_count for t in extracted_topics)
        unclustered_count = max(0, len(posts) - clustered_post_count)

        return BatchTopicResult(
            total_posts_analyzed=len(posts),
            total_topics_found=len(extracted_topics),
            topics=extracted_topics,
            unclustered_posts_count=unclustered_count,
            model=self.engine.model_name,
            analyzed_at=datetime.now(timezone.utc),
        )


# Global default instance
_default_topic_analyzer = TopicAnalysisService()


def get_topic_analyzer() -> TopicAnalysisService:
    """Returns the default TopicAnalysisService instance."""
    return _default_topic_analyzer
