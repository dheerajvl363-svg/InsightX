import io
import json
import socket
import urllib.error
from unittest.mock import MagicMock, patch
import pytest

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
    AIContext,
    EvidenceGroundedContextBuilder,
    MockAIProvider,
    OpenAIProvider,
    get_ai_provider,
)


def _create_sample_insight() -> InsightItem:
    """Helper constructing a sample InsightItem."""
    return InsightItem(
        id="ins_openai_001",
        type=InsightType.SENTIMENT_SHIFT,
        title="Negative Sentiment Shift in Product Reviews",
        summary="Dominant sentiment shifted to negative following API deprecation announcement.",
        severity=InsightSeverity.HIGH,
        confidence=0.89,
        affected_topic="Product Deprecation",
        affected_platforms=["twitter", "reddit"],
        evidence=InsightEvidence(
            topic_id="topic_dep_01",
            topic_label="Product Deprecation",
            growth_rate=120.0,
            current_volume=85,
            baseline_volume=38,
            z_score=2.85,
            sentiment_score=-0.72,
            dominant_sentiment="negative",
            post_ids=[201, 202, 203],
            external_post_ids=["tw_201", "tw_202"],
            key_authors=["@dev_advocate", "@api_user"],
            platforms=["twitter", "reddit"],
        ),
    )


def _create_sample_explanation(insight: InsightItem) -> InsightExplanation:
    """Helper constructing a sample InsightExplanation."""
    return InsightExplanation(
        insight_id=insight.id,
        type=insight.type,
        title=insight.title,
        summary=insight.summary,
        severity=insight.severity,
        confidence=insight.confidence,
        confidence_rationale="Z-score 2.85 indicates clear shift",
        severity_rationale="-0.72 sentiment score",
        facts=[
            "Sentiment polarity dropped to -0.72.",
            "85 posts detected in current window vs baseline 38.",
        ],
        interpretation="Deprecation announcement triggered sharp negative community feedback.",
        recommended_action="Prepare communication response",
        action_items=["Draft FAQ document", "Address top developer handles"],
    )


class TestOpenAIProvider:
    """Unit test suite for OpenAIProvider REST adapter."""

    def test_provider_availability_without_api_key(self):
        provider = OpenAIProvider(api_key=None)
        assert provider.provider_name == "openai"
        assert provider.is_available() is False

        provider_empty = OpenAIProvider(api_key="   ")
        assert provider_empty.is_available() is False

    def test_provider_availability_with_api_key(self):
        provider = OpenAIProvider(api_key="sk-test-key-12345")
        assert provider.provider_name == "openai"
        assert provider.is_available() is True

    def test_factory_selects_openai_when_configured(self, monkeypatch):
        import app.config
        monkeypatch.setattr(app.config, "AI_PROVIDER", "openai")
        monkeypatch.setattr(app.config, "AI_API_KEY", "sk-test-key")
        monkeypatch.setattr(app.config, "AI_ENABLED", True)

        from app.services.intelligence.ai.factory import _provider_instances
        _provider_instances.clear()

        provider = get_ai_provider("openai", model_name="gpt-4o-mini")
        assert provider.provider_name == "openai"

    def test_factory_falls_back_to_mock_when_key_missing(self, monkeypatch):
        import app.config
        monkeypatch.setattr(app.config, "AI_PROVIDER", "openai")
        monkeypatch.setattr(app.config, "AI_API_KEY", None)

        from app.services.intelligence.ai.factory import _provider_instances
        _provider_instances.clear()

        provider = get_ai_provider("openai")
        assert provider.provider_name == "mock"



    @patch("urllib.request.urlopen")
    def test_successful_openai_analysis_mocked_http(self, mock_urlopen):
        # Prepare mocked HTTP 200 response payload
        mock_response_body = {
            "id": "chatcmpl-test-123",
            "object": "chat.completion",
            "created": 1700000000,
            "model": "gpt-4o-mini",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Qualitative analysis: The deprecation notice caused developer dissatisfaction due to missing migration docs.",
                    },
                    "finish_reason": "stop",
                }
            ],
        }
        
        mock_handle = MagicMock()
        mock_handle.read.return_value = json.dumps(mock_response_body).encode("utf-8")
        mock_handle.__enter__.return_value = mock_handle
        mock_urlopen.return_value = mock_handle

        provider = OpenAIProvider(api_key="sk-valid-key")
        insight = _create_sample_insight()
        explanation = _create_sample_explanation(insight)
        request = EvidenceGroundedContextBuilder.build_request(insight=insight, explanation=explanation)

        response = provider.analyze_insight(request)

        assert response.insight_id == "ins_openai_001"
        assert "Qualitative analysis" in response.interpretation
        assert response.provider_name == "openai"
        assert response.is_flagged_unsupported is False
        assert response.grounding_metadata.is_fully_grounded is True
        assert response.grounding_metadata.supporting_post_ids == [201, 202, 203]

        # Verify outgoing HTTP request headers and payload
        assert mock_urlopen.called
        req_arg = mock_urlopen.call_args[0][0]
        assert req_arg.full_url == "https://api.openai.com/v1/chat/completions"
        assert req_arg.headers["Authorization"] == "Bearer sk-valid-key"
        
        payload_sent = json.loads(req_arg.data.decode("utf-8"))
        assert payload_sent["model"] == "gpt-4o-mini"
        assert len(payload_sent["messages"]) == 2
        assert "CRITICAL OPERATIONAL DIRECTIVES" in payload_sent["messages"][0]["content"]

    @patch("urllib.request.urlopen")
    def test_http_500_error_fallback(self, mock_urlopen):
        # Mock HTTPError 500
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://api.openai.com/v1/chat/completions",
            code=500,
            msg="Internal Server Error",
            hdrs={},
            fp=io.BytesIO(b"Internal Error"),
        )

        provider = OpenAIProvider(api_key="sk-valid-key")
        insight = _create_sample_insight()
        request = EvidenceGroundedContextBuilder.build_request(insight=insight)

        response = provider.analyze_insight(request)

        # Must NOT throw exception; must return safe deterministic fallback
        assert response.insight_id == "ins_openai_001"
        assert response.is_flagged_unsupported is True
        assert "[Fallback Interpretation]" in response.interpretation
        assert any("Provider HTTP error: HTTP 500" in note for note in response.validation_notes)

    @patch("urllib.request.urlopen")
    def test_http_timeout_fallback(self, mock_urlopen):
        mock_urlopen.side_effect = socket.timeout("Timed out waiting for connection")

        provider = OpenAIProvider(api_key="sk-valid-key", timeout=1.0)
        insight = _create_sample_insight()
        request = EvidenceGroundedContextBuilder.build_request(insight=insight)

        response = provider.analyze_insight(request)

        assert response.insight_id == "ins_openai_001"
        assert response.is_flagged_unsupported is True
        assert any("Provider network error" in note for note in response.validation_notes)

    @patch("urllib.request.urlopen")
    def test_malformed_json_fallback(self, mock_urlopen):
        mock_handle = MagicMock()
        mock_handle.read.return_value = b"NOT_VALID_JSON"
        mock_handle.__enter__.return_value = mock_handle
        mock_urlopen.return_value = mock_handle

        provider = OpenAIProvider(api_key="sk-valid-key")
        insight = _create_sample_insight()
        request = EvidenceGroundedContextBuilder.build_request(insight=insight)

        response = provider.analyze_insight(request)

        assert response.insight_id == "ins_openai_001"
        assert response.is_flagged_unsupported is True
        assert any("Provider parsing error" in note for note in response.validation_notes)

    def test_mock_provider_remains_operational(self):
        mock_provider = MockAIProvider()
        insight = _create_sample_insight()
        request = EvidenceGroundedContextBuilder.build_request(insight=insight)
        resp = mock_provider.analyze_insight(request)

        assert resp.provider_name == "mock"
        assert resp.insight_id == "ins_openai_001"
        assert resp.is_flagged_unsupported is False
