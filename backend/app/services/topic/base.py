from abc import ABC, abstractmethod
from typing import List, Optional

from app.schemas.data_quality import AnalyticsReadyPost
from app.schemas.topic import ExtractedTopic, SinglePostTopicResult


class BaseTopicEngine(ABC):
    """
    Abstract interface for topic extraction and narrative clustering backends.
    Allows swappable implementations (rule-based n-grams, TF-IDF, BERTopic, LLM)
    without modifying the service interface or downstream analytics pipelines.
    """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name and version identifier of the topic engine."""
        pass

    @abstractmethod
    def extract_post_topics(self, post: AnalyticsReadyPost) -> SinglePostTopicResult:
        """
        Extracts key terms, phrases, and candidate topic label for an individual post.
        """
        pass

    @abstractmethod
    def extract_batch_topics(self, posts: List[AnalyticsReadyPost]) -> List[ExtractedTopic]:
        """
        Clusters a collection of posts into coherent topic groups with representative labels.
        """
        pass
