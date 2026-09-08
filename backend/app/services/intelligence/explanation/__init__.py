from app.services.intelligence.explanation.base import BaseExplanationTemplate
from app.services.intelligence.explanation.cross_platform import CrossPlatformExplanationTemplate
from app.services.intelligence.explanation.emerging import EmergingTrendExplanationTemplate
from app.services.intelligence.explanation.engine import (
    DeterministicExplanationEngine,
    get_explanation_engine,
)
from app.services.intelligence.explanation.generic import GenericExplanationTemplate
from app.services.intelligence.explanation.sentiment import SentimentShiftExplanationTemplate
from app.services.intelligence.explanation.spike import AnomalousSpikeExplanationTemplate

__all__ = [
    "BaseExplanationTemplate",
    "EmergingTrendExplanationTemplate",
    "AnomalousSpikeExplanationTemplate",
    "SentimentShiftExplanationTemplate",
    "CrossPlatformExplanationTemplate",
    "GenericExplanationTemplate",
    "DeterministicExplanationEngine",
    "get_explanation_engine",
]
