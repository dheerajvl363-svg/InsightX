import json
import logging
import socket
from datetime import datetime, timezone
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

import app.config
from app.services.intelligence.ai.base import BaseAIProvider
from app.services.intelligence.ai.context_builder import EvidenceGroundedContextBuilder
from app.services.intelligence.ai.grounding import extract_grounding_metadata, validate_grounding
from app.services.intelligence.ai.schemas import (
    AIAnalysisRequest,
    AIAnalysisResponse,
    AIContext,
)

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseAIProvider):
    """
    Production-capable OpenAI REST API provider adapter implementing BaseAIProvider.
    
    Architectural Boundaries:
    - Never discovers or invents factual telemetry.
    - Strictly consumes EvidenceGroundedContextBuilder output payloads.
    - Catches all network/HTTP/JSON exceptions gracefully, falling back to deterministic explanation.
    - Passes every response through validate_grounding to enforce evidence boundary rules.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        chosen_model = model_name or getattr(app.config, "AI_MODEL_NAME", "gpt-4o-mini")
        if not chosen_model or chosen_model == "insightx-mock-ai-v1":
            chosen_model = "gpt-4o-mini"
        self._model_name = chosen_model
        self._api_key = api_key
        self._api_base_override = api_base
        self._timeout_override = timeout

    @property
    def api_key(self) -> Optional[str]:
        return self._api_key if self._api_key is not None else getattr(app.config, "AI_API_KEY", None)

    @property
    def api_base(self) -> str:
        base = self._api_base_override or getattr(app.config, "AI_API_BASE", "https://api.openai.com/v1")
        return base.rstrip("/")

    @property
    def timeout(self) -> float:
        return self._timeout_override if self._timeout_override is not None else getattr(app.config, "AI_TIMEOUT_SECONDS", 10.0)

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model_name

    def is_available(self) -> bool:
        """
        Returns True if AI is enabled and a valid API key is configured.
        """
        ai_enabled = getattr(app.config, "AI_ENABLED", True)
        if not ai_enabled:
            return False
        key = self.api_key
        if not key or not isinstance(key, str) or not key.strip():
            return False
        return True


    def analyze_insight(self, request: AIAnalysisRequest) -> AIAnalysisResponse:
        """
        Executes AI analysis for a single insight using the OpenAI REST API.
        Falls back safely to deterministic explanation on any API or network failure.
        """
        ctx: AIContext = request.context
        now = datetime.now(timezone.utc)

        # 1. Verification of provider availability
        if not self.is_available():
            return self._build_fallback_response(
                ctx=ctx,
                reason="AI_API_KEY not configured or AI_ENABLED is false",
                now=now,
            )

        # 2. Format messages using EvidenceGroundedContextBuilder
        messages_dict = EvidenceGroundedContextBuilder.format_llm_messages(
            context=ctx,
            prompt_instructions=request.prompt_instructions,
        )

        payload: Dict[str, Any] = {
            "model": self._model_name,
            "messages": [
                {"role": "system", "content": messages_dict["system_prompt"]},
                {"role": "user", "content": messages_dict["user_context_block"]},
            ],
            "temperature": 0.2,
        }

        url = f"{self.api_base}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "InsightX-Intelligence-Engine/1.0",
        }

        # 3. HTTP Request Execution with robust exception handling
        try:
            req_data = json.dumps(payload).encode("utf-8")
            http_req = urllib.request.Request(url, data=req_data, headers=headers, method="POST")

            with urllib.request.urlopen(http_req, timeout=self.timeout) as resp:

                resp_bytes = resp.read()
                data = json.loads(resp_bytes.decode("utf-8"))

            content = data["choices"][0]["message"]["content"]
            parsed_response = self._parse_llm_content(content=content, ctx=ctx, now=now)
            return validate_grounding(ctx, parsed_response)

        except urllib.error.HTTPError as e:
            err_msg = f"HTTP {e.code}: {e.reason}"
            logger.warning(f"OpenAI API HTTP Error for insight '{ctx.insight_id}': {err_msg}")
            return self._build_fallback_response(ctx=ctx, reason=f"Provider HTTP error: {err_msg}", now=now)

        except (urllib.error.URLError, socket.timeout, TimeoutError) as e:
            err_msg = f"Network timeout/connection error: {e}"
            logger.warning(f"OpenAI API Network Error for insight '{ctx.insight_id}': {err_msg}")
            return self._build_fallback_response(ctx=ctx, reason=f"Provider network error: {err_msg}", now=now)

        except (json.JSONDecodeError, KeyError, IndexError) as e:
            err_msg = f"Malformed response payload: {e}"
            logger.warning(f"OpenAI API Parsing Error for insight '{ctx.insight_id}': {err_msg}")
            return self._build_fallback_response(ctx=ctx, reason=f"Provider parsing error: {err_msg}", now=now)

        except Exception as e:
            err_msg = f"Unexpected error: {e}"
            logger.error(f"OpenAI API Unexpected Error for insight '{ctx.insight_id}': {err_msg}", exc_info=True)
            return self._build_fallback_response(ctx=ctx, reason=f"Provider failure: {err_msg}", now=now)

    def _parse_llm_content(self, content: str, ctx: AIContext, now: datetime) -> AIAnalysisResponse:
        """
        Parses raw text response from OpenAI LLM into structured AIAnalysisResponse.
        """
        interpretation = content.strip()
        recommendations: List[str] = [
            f"Review primary telemetry posts for '{ctx.affected_topic or ctx.title}'.",
            "Monitor platform distribution over the next evaluation cycle.",
        ]
        if ctx.severity in ("critical", "high"):
            recommendations.append("Alert operational leads for urgent triage.")

        confidence_assessment = (
            f"AI qualitative interpretation generated for statistical signal (confidence={ctx.confidence:.2f})."
        )

        initial = AIAnalysisResponse(
            insight_id=ctx.insight_id,
            interpretation=interpretation,
            ai_recommendations=recommendations,
            confidence_assessment=confidence_assessment,
            grounding_metadata=extract_grounding_metadata(ctx),
            provider_name=self.provider_name,
            model_name=self.model_name,
            generated_at=now,
            is_flagged_unsupported=False,
            validation_notes=[],
        )
        return initial

    def _build_fallback_response(self, ctx: AIContext, reason: str, now: datetime) -> AIAnalysisResponse:
        """
        Constructs a safe, deterministic fallback response when provider calls fail or are disabled.
        """
        fallback_interp = (
            f"[Fallback Interpretation] {ctx.title} ({ctx.severity.value.upper()} priority): "
            f"{ctx.summary} (Deterministic baseline used due to AI provider fallback)."
        )

        fallback_recs: List[str] = [
            f"Review supporting telemetry posts (total count={ctx.total_supporting_post_count}).",
            "Execute standard operational triage procedures.",
        ]

        resp = AIAnalysisResponse(
            insight_id=ctx.insight_id,
            interpretation=fallback_interp,
            ai_recommendations=fallback_recs,
            confidence_assessment="Deterministic explanation baseline retained due to provider fallback.",
            grounding_metadata=extract_grounding_metadata(ctx),
            provider_name=self.provider_name,
            model_name=self.model_name,
            generated_at=now,
            is_flagged_unsupported=True,
            validation_notes=[reason],
        )
        return validate_grounding(ctx, resp)
