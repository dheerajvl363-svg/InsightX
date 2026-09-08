from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict

from app.schemas.sentiment import SentimentLabel, SentimentProbabilities


@dataclass
class SentimentInferenceResult:
    """Internal model output structure produced by sentiment engine implementations."""
    label: SentimentLabel
    score: float
    confidence: float
    probabilities: SentimentProbabilities
    model_name: str
    details: Dict[str, Any] = field(default_factory=dict)


class BaseSentimentEngine(ABC):
    """
    Abstract interface for sentiment analysis inference backends.
    Allows swappable implementations (rule-based, lexicon, transformer, classical ML)
    without altering the service interface or downstream analytics pipelines.
    """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name and version identifier of the model."""
        pass

    @abstractmethod
    def analyze_text(self, text: str) -> SentimentInferenceResult:
        """
        Runs sentiment analysis inference on the input text.
        Returns a SentimentInferenceResult.
        """
        pass
