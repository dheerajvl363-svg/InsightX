# Implementation Plan - Phase 7.3.4: AI Interpretation API & Unified Workflow Integration

Expose AI-assisted interpretation through the FastAPI intelligence API (`POST /api/v1/intelligence/insights/{insight_id}/ai-interpret`) and integrate AI capabilities cleanly into `UnifiedIntelligenceWorkflow`.

## Core Architectural Principle
**DETERMINISTIC ANALYTICS = SOURCE OF TRUTH**  
**EVIDENCE = PROOF**  
**DETERMINISTIC EXPLANATION = AUDITABLE BASELINE**  
**LLM = INTERPRETATION / COMMUNICATION ASSISTANT**  

Deterministic analytics remain the sole source of truth. AI is an optional qualitative interpretation layer. AI provider failures will gracefully return deterministic baselines and never break API endpoints.

---

## Architectural Flow

```
Raw Posts / DB Telemetry
         │
         ▼
Deterministic Multi-Facet Analytics (Sentiment, Topics, Trends, Network, Overview)
         │
         ▼
Deterministic Intelligence Engine (InsightItem + Evidence)
         │
         ▼
Deterministic Explanation Engine (InsightExplanation + Facts)
         │
         ▼
EvidenceGroundedContextBuilder (AIContext + System Prompt + Untrusted Content Delimiting)
         │
         ▼
AI Provider (OpenAIProvider / MockAIProvider)
         │
         ▼
Grounding Validation (validate_grounding)
         │
         ├──▶ Success ──▶ AI Interpretation & Recommendations
         └──▶ Error/Fallback ──▶ Baseline Explanation with Fallback Warning Flag
         │
         ▼
POST /api/v1/intelligence/insights/{insight_id}/ai-interpret  (AIInterpretationResponse)
```

---

## Proposed Changes

### Backend Schemas

#### [MODIFY] [intelligence.py](file:///Users/mohammedanas/InsightX/backend/app/schemas/intelligence.py)
Add AI interpretation request/response schemas:
- `AIInterpretationRequest`:
  - `platform`: Optional[str] = None
  - `prompt_instructions`: Optional[str] = None
  - `max_post_ids`: Optional[int] = 25
- `AIInterpretationResponse`:
  - `insight_id`: str
  - `insight`: InsightItem (deterministic insight)
  - `explanation`: InsightExplanation (deterministic explanation)
  - `ai_analysis`: AIAnalysisResponse (AI qualitative interpretation, recommendations, grounding metadata)
  - `is_fallback_used`: bool
  - `generated_at`: datetime
- Update `UnifiedWorkflowResult`:
  - Add optional field `ai_analyses: List[AIAnalysisResponse] = Field(default_factory=list)`

---

### Backend Intelligence Services

#### [MODIFY] [workflow.py](file:///Users/mohammedanas/InsightX/backend/app/services/intelligence/workflow.py)
Update `UnifiedIntelligenceWorkflow`:
- In `__init__`, inject `ai_service: Optional[AIAssistedIntelligenceService] = None` (defaults to `get_ai_intelligence_service()`).
- In `run_workflow`: Add optional parameter `include_ai: bool = False`.
  - When `include_ai=False` (default): Behaves 100% identically to existing Phase 7.2.6 implementation.
  - When `include_ai=True`: After generating explanations, invokes `self.ai_service.analyze_batch()` and populates `ai_analyses` on `UnifiedWorkflowResult`.
- Add method `get_ai_interpretation(insight_id: str, platform: Optional[str] = None, prompt_instructions: Optional[str] = None, db: Optional[Session] = None) -> AIInterpretationResponse`:
  - Resolves insight and explanation via `get_insight_explanation()`.
  - Invokes `ai_service.analyze_insight()`.
  - Determines if fallback was used (`is_fallback_used = ai_analysis.is_flagged_unsupported`).
  - Assembles and returns auditable `AIInterpretationResponse`.

---

### Backend API Routes

#### [MODIFY] [intelligence.py](file:///Users/mohammedanas/InsightX/backend/app/api/routes/intelligence.py)
Add new API endpoint:
- `POST /api/v1/intelligence/insights/{insight_id}/ai-interpret`:
  - Endpoint handler: `get_ai_interpretation_for_insight()`
  - Accepts `insight_id: str`, optional `request: Optional[AIInterpretationRequest] = None`, `workflow: UnifiedIntelligenceWorkflow = Depends(get_workflow_instance)`, `db: Session = Depends(get_db)`.
  - Invokes `workflow.get_ai_interpretation()`.
  - Handles `LookupError` (404 Not Found if insight ID does not exist).
  - Handles `ValueError` (400 Bad Request).
  - Catches unexpected errors gracefully (500 Internal Server Error).
  - **Security Guarantee**: Never accepts API keys in request payload. Secrets remain strictly environment-managed.

Update `POST /analyze` in `intelligence.py`:
- Update `IntelligenceAnalyzeRequest` to support `include_ai: Optional[bool] = False`.
- If `include_ai=True`, populates `item.metadata["ai_analysis"]` on returned insights.

---

### Backend Unit Tests

#### [NEW] [test_phase7_ai_api.py](file:///Users/mohammedanas/InsightX/backend/tests/test_phase7_ai_api.py)
Add comprehensive test suite covering:
1. `POST /api/v1/intelligence/insights/{id}/ai-interpret` with `MockAIProvider` (200 OK with structured `AIInterpretationResponse`).
2. `POST /api/v1/intelligence/insights/{id}/ai-interpret` with mocked `OpenAIProvider` success.
3. Fallback handling on AI provider error / missing key (returns 200 OK with `is_fallback_used=True` and deterministic explanation).
4. Grounding validation integration on API response.
5. Unknown `insight_id` handling (returns 404 Not Found).
6. Unified workflow execution with `include_ai=False` (default, preserves exact existing behavior).
7. Unified workflow execution with `include_ai=True` (populates `ai_analyses`).
8. `POST /analyze` with `include_ai=True`.
9. Backward compatibility verification for `GET /insights`, `GET /insights/{id}/explanation`, `GET /insights/unified`.
10. Zero real network calls made during tests.

---

## Verification Plan

### Automated Tests
- Run `PYTHONPATH=backend backend/.venv/bin/pytest backend/tests/test_phase7_ai_api.py`
- Run `PYTHONPATH=backend backend/.venv/bin/pytest backend/tests/test_phase7_ai_provider_openai.py`
- Run `PYTHONPATH=backend backend/.venv/bin/pytest backend/tests/test_phase7_ai_context_builder.py`
- Run `PYTHONPATH=backend backend/.venv/bin/pytest backend/tests/test_phase7_ai_architecture.py`
- Run full backend test suite `PYTHONPATH=backend backend/.venv/bin/pytest backend/tests/`
- Run frontend build `npm run build` in `frontend/`
- Run `git diff --check` and `git status`
