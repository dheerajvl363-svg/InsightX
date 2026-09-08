from typing import List

from app.services.intelligence.ai.schemas import (
    AIAnalysisResponse,
    AIContext,
    AIGroundingMetadata,
)


def extract_grounding_metadata(context: AIContext) -> AIGroundingMetadata:
    """
    Extracts explicit provenance metadata directly from an AIContext object.
    Ensures metadata is anchored to factual telemetry rather than LLM assertions.
    """
    has_evidence = bool(
        context.supporting_post_ids
        or context.external_post_ids
        or context.facts
        or context.deterministic_metrics
    )

    return AIGroundingMetadata(
        insight_id=context.insight_id,
        evidence_topic_id=None,
        evidence_topic_label=context.affected_topic,
        supporting_post_ids=list(context.supporting_post_ids),
        external_post_ids=list(context.external_post_ids),
        platforms=list(context.affected_platforms),
        time_window=context.time_window,
        deterministic_metrics_used=dict(context.deterministic_metrics),
        facts_count=len(context.facts),
        is_fully_grounded=has_evidence,
    )


def validate_grounding(
    context: AIContext,
    response: AIAnalysisResponse,
) -> AIAnalysisResponse:
    """
    Validates and enforces evidence grounding boundaries on an AIAnalysisResponse.
    
    Rules:
    1. Attaches verified AIGroundingMetadata extracted directly from the deterministic context.
    2. If context is missing supporting posts and facts, flags response as unsupported (is_flagged_unsupported=True).
    3. Guarantees evidence and post IDs match context exactly.
    """
    notes: List[str] = list(response.validation_notes)
    
    grounding_meta = extract_grounding_metadata(context)
    
    # Flag missing or ungrounded context
    if not grounding_meta.is_fully_grounded:
        notes.append("Flagged: Context lacks supporting post IDs, facts, or deterministic metrics.")
        response.is_flagged_unsupported = True
    
    # Verify ID match
    if response.insight_id != context.insight_id:
        notes.append(f"Warning: Response insight_id '{response.insight_id}' mismatched context '{context.insight_id}'. Overwriting.")
        response.insight_id = context.insight_id

    response.grounding_metadata = grounding_meta
    response.validation_notes = notes

    return response
