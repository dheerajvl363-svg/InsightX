from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict

from app.schemas.emotion import EmotionLabel, EmotionProbabilities


@dataclass
class EmotionInferenceResult:
    """Internal model output structure produced by emotion engine implementations."""
    primary_emotion: EmotionLabel
    confidence: float
    probabilities: EmotionProbabilities
    model_name: str
    details: Dict[str, Any] = field(default_factory=dict)


class BaseEmotionEngine(ABC):
    """
    Abstract interface for emotion analysis inference backends.
    Allows swappable implementations (rule-based lexicon, fine-tuned transformer, classical ML)
    without modifying the service interface or downstream analytics pipelines.
    """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name and version identifier of the emotion model."""
        pass

    @abstractmethod
    def analyze_text(self, text: str) -> EmotionInferenceResult:
        """
        Runs emotion detection inference on the input text.
        Returns an EmotionInferenceResult with dominant emotion and probability distribution.
        """
        pass
