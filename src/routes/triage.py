import os
from fastapi import APIRouter, HTTPException
from src.llm.schema import TriageInput, TriageOutput, CategoryEnum, UrgencyEnum, TeamEnum
from src.llm.service import execute_triage_pipeline

router = APIRouter()


@router.post("/triage", response_model=TriageOutput)
async def triage_ticket(payload: TriageInput) -> TriageOutput:
    # 1. Kill Switch Check (LLM_ENABLED=false)
    if os.environ.get("LLM_ENABLED", "true").lower() == "false":
        return TriageOutput(
            category=CategoryEnum.other,
            urgency=UrgencyEnum.normal,
            suggested_team=TeamEnum.triage,
            confidence=0.0,
            reason="Kill switch active (LLM_ENABLED=false). Deterministic fallback routing engaged.",
        )

    # 2. Stage 1 Stub Mode
    if os.environ.get("LLM_STUB") == "1":
        return TriageOutput(
            category=CategoryEnum.billing,
            urgency=UrgencyEnum.high,
            suggested_team=TeamEnum.finance,
            confidence=0.95,
            reason="Stub response: Customer reported a duplicate charge on their invoice.",
        )

    # 3. Production Pipeline Execution
    result, is_timeout = execute_triage_pipeline(payload.text)

    if is_timeout:
        raise HTTPException(
            status_code=504,
            detail={"error": "Gateway Timeout", "message": "Upstream LLM inference exceeded the 30-second deadline."},
        )

    if result is None:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "Unprocessable Content",
                "message": "Model generated invalid data that failed repair against the schema. Quarantined for review.",
            },
        )

    return result
