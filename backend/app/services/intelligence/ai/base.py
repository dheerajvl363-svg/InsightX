from abc import ABC, abstractmethod
from typing import List

from app.services.intelligence.ai.schemas import (
    AIAnalysisRequest,
    AIAnalysisResponse,
)


class BaseAIProvider(ABC):
    """
    Provider-agnostic interface for AI-assisted interpretation engines.
    
    Guarantees a unified contract across mock providers and future external LLM adapters
    (e.g., OpenAI, Anthropic, Gemini, or local models).
    
    Core Architectural Boundary:
    The AI provider is strictly an interpretation and communication assistant.
    It receives deterministic facts and evidence via AIAnalysisRequest and MUST NOT
    discover, invent, or fabricate factual telemetry or post records.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Returns the unique identifier of the provider implementation (e.g., 'mock', 'openai')."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Returns the model version string (e.g., 'insightx-mock-ai-v1', 'gpt-4o')."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Checks whether the provider is configured and operational.
        Returns True for mock/no-op providers, or verifies API keys/credentials for external LLMs.
        """
        pass

    @abstractmethod
    def analyze_insight(self, request: AIAnalysisRequest) -> AIAnalysisResponse:
        """
        Generates a structured AI analysis response for a single insight request.
        Must strictly adhere to evidence-grounding constraints.
        """
        pass

    def batch_analyze_insights(
        self,
        requests: List[AIAnalysisRequest],
    ) -> List[AIAnalysisResponse]:
        """
        Batch processes multiple insight interpretation requests.
        Default implementation iterates over requests sequentially.
        """
        return [self.analyze_insight(req) for req in requests]
