import os
from fastapi import APIRouter, HTTPException
from src.llm.schema import TriageInput, TriageOutput, CategoryEnum, UrgencyEnum, TeamEnum
from src.llm.service import execute_triage_with_repair

router = APIRouter()


@router.post("/triage", response_model=TriageOutput)
async def triage_ticket(payload: TriageInput) -> TriageOutput:
    # Stage 1: Stub mode check
    if os.environ.get("LLM_STUB") == "1":
        return TriageOutput(
            category=CategoryEnum.billing,
            urgency=UrgencyEnum.high,
            suggested_team=TeamEnum.finance,
            confidence=0.95,
            reason="Stub response: Customer reported a duplicate charge on their invoice.",
        )

    # Stage 3: Parse, validate, repair once, quarantine on failure
    result = execute_triage_with_repair(payload.text)
    if result is None:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "Unprocessable Content",
                "message": "Model generated invalid data that failed repair against the schema. Quarantined for review.",
            },
        )

    return result
