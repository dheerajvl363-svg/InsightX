import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.intelligence import (
    BatchInsightResult,
    InsightExplanation,
    IntelligenceAnalyzeRequest,
    UnifiedWorkflowResult,
)
from app.services.intelligence.ai import (
    AIInterpretationRequest,
    AIInterpretationResponse,
)
from app.services.intelligence.workflow import (
    UnifiedIntelligenceWorkflow,
    get_unified_workflow,
)



logger = logging.getLogger(__name__)

router = APIRouter(tags=["Intelligence"])


def get_workflow_instance(db: Session = Depends(get_db)) -> UnifiedIntelligenceWorkflow:
    """Dependency provider resolving the unified intelligence workflow."""
    return get_unified_workflow(db=db)


@router.get(
    "/insights",
    response_model=BatchInsightResult,
    summary="Fetch Recent Insights",
    description="Generates and returns synthesized insights based on recent platform data.",
)
def get_insights(
    platform: Optional[str] = Query(None, description="Filter by platform name"),
    min_confidence: float = Query(0.5, ge=0.0, le=1.0, description="Minimum confidence threshold"),
    max_insights: int = Query(20, ge=1, le=100, description="Maximum insights to return"),
    workflow: UnifiedIntelligenceWorkflow = Depends(get_workflow_instance),
    db: Session = Depends(get_db),
) -> BatchInsightResult:
    try:
        report = workflow.run_workflow(
            db=db,
            platform=platform,
            min_confidence=min_confidence,
            max_insights=max_insights,
            generate_explanations=False,
        )
        return report.batch_insights
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating insights: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while synthesizing intelligence.",
        )


@router.get(
    "/insights/unified",
    response_model=UnifiedWorkflowResult,
    summary="Run Unified Intelligence Workflow",
    description="Executes the complete unified workflow returning multi-facet telemetry, insights, and explanations.",
)
def get_unified_report(
    platform: Optional[str] = Query(None, description="Filter by platform name"),
    min_confidence: float = Query(0.5, ge=0.0, le=1.0, description="Minimum confidence threshold"),
    max_insights: int = Query(20, ge=1, le=100, description="Maximum insights to return"),
    workflow: UnifiedIntelligenceWorkflow = Depends(get_workflow_instance),
    db: Session = Depends(get_db),
) -> UnifiedWorkflowResult:
    try:
        return workflow.run_workflow(
            db=db,
            platform=platform,
            min_confidence=min_confidence,
            max_insights=max_insights,
            generate_explanations=True,
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error running unified workflow: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while executing the unified workflow.",
        )


@router.get(
    "/insights/{insight_id}/explanation",
    response_model=InsightExplanation,
    summary="Get Insight Explanation",
    description="Returns the detailed, human-readable evidence and explanation for a specific insight.",
)
def get_insight_explanation(
    insight_id: str,
    platform: Optional[str] = Query(None, description="Filter by platform name (must match original GET /insights query)"),
    workflow: UnifiedIntelligenceWorkflow = Depends(get_workflow_instance),
    db: Session = Depends(get_db),
) -> InsightExplanation:
    try:
        try:
            return workflow.get_insight_explanation(insight_id=insight_id, platform=platform, db=db)
        except LookupError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Insight {insight_id} not found in recent generated insights.",
            )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating explanation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while generating the explanation.",
        )


@router.post(
    "/insights/{insight_id}/ai-interpret",
    response_model=AIInterpretationResponse,
    summary="Generate AI Interpretation for Insight",
    description="Generates an evidence-grounded, AI-assisted qualitative interpretation for a specific insight.",
)
def get_ai_interpretation_for_insight(
    insight_id: str,
    payload: Optional[AIInterpretationRequest] = None,
    workflow: UnifiedIntelligenceWorkflow = Depends(get_workflow_instance),
    db: Session = Depends(get_db),
) -> AIInterpretationResponse:
    req_payload = payload or AIInterpretationRequest()
    try:
        return workflow.get_ai_interpretation(
            insight_id=insight_id,
            platform=req_payload.platform,
            prompt_instructions=req_payload.prompt_instructions,
            max_post_ids=req_payload.max_post_ids,
            raw_posts=req_payload.raw_posts,
            db=db,
        )
    except LookupError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Insight {insight_id} not found in recent synthesized intelligence.",
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating AI interpretation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while generating AI interpretation.",
        )


@router.post(
    "/analyze",
    response_model=BatchInsightResult,
    summary="Analyze Payload for Insights",
    description="Generates insights based on a provided payload of posts or pre-computed trends.",
)
def analyze_payload(
    payload: IntelligenceAnalyzeRequest,
    workflow: UnifiedIntelligenceWorkflow = Depends(get_workflow_instance),
) -> BatchInsightResult:
    try:
        if not payload.posts and not payload.raw_posts and not payload.trends and not payload.topics:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payload must contain at least posts, raw_posts, trends, or topics.",
            )

        report = workflow.run_workflow(
            posts=payload.posts,
            raw_posts=payload.raw_posts,
            topics=payload.topics,
            trends=payload.trends,
            platform=payload.platform,
            min_confidence=payload.min_confidence or 0.5,
            max_insights=payload.max_insights or 20,
            generate_explanations=bool(payload.include_explanations or payload.include_ai),
            include_ai=bool(payload.include_ai),
        )

        batch_result = report.batch_insights
        if payload.include_explanations and report.explanations:
            expl_map = {e.insight_id: e.model_dump() for e in report.explanations}
            for item in batch_result.insights:
                if item.id in expl_map:
                    item.metadata["explanation"] = expl_map[item.id]

        if payload.include_ai and report.ai_analyses:
            ai_map = {a.insight_id: a.model_dump() for a in report.ai_analyses}
            for item in batch_result.insights:
                if item.id in ai_map:
                    item.metadata["ai_analysis"] = ai_map[item.id]

        return batch_result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error analyzing intelligence payload: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during payload analysis.",
        )
