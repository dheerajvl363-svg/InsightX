from datetime import datetime, timezone
import pytest

from app.config import AI_PROVIDER
from app.schemas.intelligence import (
    InsightEvidence,
    InsightExplanation,
    InsightItem,
    InsightSeverity,
    InsightType,
)
from app.services.intelligence.ai import (
    AIAssistedIntelligenceService,
    AIAnalysisRequest,
    AIAnalysisResponse,
    AIContext,
    AIGroundingMetadata,
    BaseAIProvider,
    MockAIProvider,
    extract_grounding_metadata,
    get_ai_intelligence_service,
    get_ai_provider,
    register_ai_provider,
    validate_grounding,
)


def _create_sample_insight(
    insight_id: str = "ins_test_001",
    has_post_ids: bool = True,
    has_metrics: bool = True,
) -> InsightItem:
    """Helper creating a sample InsightItem for testing."""
    post_ids = [101, 102, 103] if has_post_ids else []
    ext_ids = ["tw_101", "tw_102"] if has_post_ids else []
    
    return InsightItem(
        id=insight_id,
        type=InsightType.EMERGING_TREND,
        title="Spike in AI Infrastructure Discussion",
        summary="Rapid emergence of AI compute cluster performance topics observed across platforms.",
        severity=InsightSeverity.HIGH,
        confidence=0.88,
        affected_topic="AI Infrastructure",
        affected_platforms=["twitter", "reddit"],
        evidence=InsightEvidence(
            topic_id="topic_ai_01",
            topic_label="AI Infrastructure",
            growth_rate=145.5 if has_metrics else None,
            current_volume=350 if has_metrics else None,
            baseline_volume=142 if has_metrics else None,
            z_score=3.25 if has_metrics else None,
            sentiment_score=0.45 if has_metrics else None,
            dominant_sentiment="positive" if has_metrics else None,
            post_ids=post_ids,
            external_post_ids=ext_ids,
            key_authors=["@tech_analyst", "@gpu_guru"],
            platforms=["twitter", "reddit"],
        ),
        recommended_action="Assess capacity impact",
        action_items=["Monitor GPU telemetry", "Review post feedback"],
    )


def _create_sample_explanation(insight: InsightItem) -> InsightExplanation:
    """Helper creating a sample InsightExplanation for testing."""
    return InsightExplanation(
        insight_id=insight.id,
        type=insight.type,
        title=insight.title,
        summary=insight.summary,
        severity=insight.severity,
        confidence=insight.confidence,
        confidence_rationale="Z-score 3.25 indicates strong anomaly",
        severity_rationale="High volume growth (+145.5%)",
        facts=[
            "Post volume grew by +145.5% compared to historical baseline.",
            "350 posts observed in current evaluation window.",
            "Z-score of 3.25 standard deviations above mean.",
        ],
        interpretation="Strong evidence of sudden community interest in AI hardware.",
        recommended_action=insight.recommended_action,
        action_items=insight.action_items,
    )


class TestAIProviderContract:
    """Tests for BaseAIProvider abstract interface and contract enforcement."""

    def test_base_provider_cannot_be_instantiated(self):
        with pytest.raises(TypeError):
            BaseAIProvider()

    def test_custom_provider_implementation(self):
        class CustomTestProvider(BaseAIProvider):
            @property
            def provider_name(self) -> str:
                return "custom_test"

            @property
            def model_name(self) -> str:
                return "custom-v1"

            def is_available(self) -> bool:
                return True

            def analyze_insight(self, request: AIAnalysisRequest) -> AIAnalysisResponse:
                meta = extract_grounding_metadata(request.context)
                return AIAnalysisResponse(
                    insight_id=request.context.insight_id,
                    interpretation="Custom interpretation string",
                    ai_recommendations=["Recommendation 1"],
                    grounding_metadata=meta,
                    provider_name=self.provider_name,
                    model_name=self.model_name,
                )

        provider = CustomTestProvider()
        assert provider.provider_name == "custom_test"
        assert provider.model_name == "custom-v1"
        assert provider.is_available() is True

        insight = _create_sample_insight()
        ctx = AIContext.from_insight_and_explanation(insight)
        req = AIAnalysisRequest(context=ctx)
        resp = provider.analyze_insight(req)
        assert resp.interpretation == "Custom interpretation string"
        assert resp.provider_name == "custom_test"


class TestAIContextConstruction:
    """Tests for AIContext model generation from deterministic outputs."""

    def test_context_creation_from_insight_and_explanation(self):
        insight = _create_sample_insight()
        explanation = _create_sample_explanation(insight)
        
        context = AIContext.from_insight_and_explanation(insight, explanation)
        
        assert context.insight_id == "ins_test_001"
        assert context.type == InsightType.EMERGING_TREND
        assert context.title == "Spike in AI Infrastructure Discussion"
        assert context.severity == InsightSeverity.HIGH
        assert context.confidence == 0.88
        assert context.affected_topic == "AI Infrastructure"
        assert context.affected_platforms == ["twitter", "reddit"]
        assert len(context.facts) == 3
        assert context.facts[0].startswith("Post volume grew by")
        assert context.deterministic_metrics["z_score"] == 3.25
        assert context.deterministic_metrics["growth_rate"] == 145.5
        assert context.supporting_post_ids == [101, 102, 103]
        assert context.external_post_ids == ["tw_101", "tw_102"]
        assert context.key_authors == ["@tech_analyst", "@gpu_guru"]

    def test_context_creation_without_explanation(self):
        insight = _create_sample_insight()
        context = AIContext.from_insight_and_explanation(insight, explanation=None)
        
        assert context.insight_id == "ins_test_001"
        assert context.facts == []
        assert context.deterministic_metrics["z_score"] == 3.25
        assert context.supporting_post_ids == [101, 102, 103]


class TestMockAIProvider:
    """Tests for MockAIProvider behavior and safety."""

    def test_mock_provider_properties(self):
        provider = MockAIProvider(model_name="test-mock-v1")
        assert provider.provider_name == "mock"
        assert provider.model_name == "test-mock-v1"
        assert provider.is_available() is True

    def test_mock_provider_analyze_insight(self):
        provider = MockAIProvider()
        insight = _create_sample_insight()
        explanation = _create_sample_explanation(insight)
        context = AIContext.from_insight_and_explanation(insight, explanation)
        
        request = AIAnalysisRequest(context=context, prompt_instructions="Highlight infra implications")
        response = provider.analyze_insight(request)

        assert response.insight_id == "ins_test_001"
        assert "AI Assessment (HIGH priority)" in response.interpretation
        assert "Highlight infra implications" in response.interpretation
        assert len(response.ai_recommendations) <= 3
        assert response.provider_name == "mock"
        assert response.is_flagged_unsupported is False
        assert response.grounding_metadata.is_fully_grounded is True
        assert response.grounding_metadata.supporting_post_ids == [101, 102, 103]

    def test_mock_provider_batch_analysis(self):
        provider = MockAIProvider()
        i1 = _create_sample_insight("ins_01")
        i2 = _create_sample_insight("ins_02")
        
        reqs = [
            AIAnalysisRequest(context=AIContext.from_insight_and_explanation(i1)),
            AIAnalysisRequest(context=AIContext.from_insight_and_explanation(i2)),
        ]
        responses = provider.batch_analyze_insights(reqs)
        
        assert len(responses) == 2
        assert responses[0].insight_id == "ins_01"
        assert responses[1].insight_id == "ins_02"


class TestGroundingValidationAndProvenance:
    """Tests for grounding validation and missing evidence handling."""

    def test_provenance_preservation(self):
        insight = _create_sample_insight()
        context = AIContext.from_insight_and_explanation(insight)
        meta = extract_grounding_metadata(context)

        assert meta.insight_id == "ins_test_001"
        assert meta.evidence_topic_label == "AI Infrastructure"
        assert meta.supporting_post_ids == [101, 102, 103]
        assert meta.external_post_ids == ["tw_101", "tw_102"]
        assert meta.platforms == ["twitter", "reddit"]
        assert meta.deterministic_metrics_used["growth_rate"] == 145.5
        assert meta.is_fully_grounded is True

    def test_unsupported_missing_evidence_handling(self):
        # Create insight with NO post IDs and NO metrics
        bare_insight = _create_sample_insight(has_post_ids=False, has_metrics=False)
        context = AIContext.from_insight_and_explanation(bare_insight, explanation=None)
        
        assert context.supporting_post_ids == []
        assert context.facts == []
        assert context.deterministic_metrics == {}

        provider = MockAIProvider()
        request = AIAnalysisRequest(context=context)
        response = provider.analyze_insight(request)

        # Must flag as unsupported due to lack of grounded evidence
        assert response.is_flagged_unsupported is True
        assert response.grounding_metadata.is_fully_grounded is False
        assert any("Context lacks supporting post IDs" in note for note in response.validation_notes)


class TestAIProviderFactoryAndService:
    """Tests for get_ai_provider factory and AIAssistedIntelligenceService."""

    def test_get_ai_provider_default(self):
        provider = get_ai_provider()
        assert provider is not None
        assert isinstance(provider, BaseAIProvider)
        assert provider.provider_name == "mock"

    def test_get_ai_provider_explicit_mock(self):
        provider = get_ai_provider("mock", model_name="custom-mock-v2")
        assert provider.provider_name == "mock"
        assert provider.model_name == "custom-mock-v2"

    def test_provider_registration_extensibility(self):
        class FutureDummyAdapter(BaseAIProvider):
            @property
            def provider_name(self) -> str:
                return "future_dummy"

            @property
            def model_name(self) -> str:
                return "dummy-v1"

            def is_available(self) -> bool:
                return True

            def analyze_insight(self, request: AIAnalysisRequest) -> AIAnalysisResponse:
                meta = extract_grounding_metadata(request.context)
                return AIAnalysisResponse(
                    insight_id=request.context.insight_id,
                    interpretation="Dummy interpretation",
                    grounding_metadata=meta,
                    provider_name=self.provider_name,
                    model_name=self.model_name,
                )

        register_ai_provider("future_dummy", FutureDummyAdapter)
        p = get_ai_provider("future_dummy")
        assert p.provider_name == "future_dummy"

    def test_ai_assisted_intelligence_service(self):
        service = get_ai_intelligence_service()
        insight = _create_sample_insight()
        explanation = _create_sample_explanation(insight)

        resp = service.analyze_insight(insight, explanation)
        assert resp.insight_id == "ins_test_001"
        assert resp.provider_name == "mock"
        assert resp.grounding_metadata.supporting_post_ids == [101, 102, 103]
