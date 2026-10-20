import os
from fastapi import APIRouter, HTTPException
from src.llm.schema import TriageInput, TriageOutput, CategoryEnum, UrgencyEnum, TeamEnum

router = APIRouter()

@router.post("/triage", response_model=TriageOutput)
async def triage_ticket(payload: TriageInput) -> TriageOutput:
    # Stage 1: Stub mode check — skips the model entirely when LLM_STUB=1
    if os.environ.get("LLM_STUB") == "1":
        return TriageOutput(
            category=CategoryEnum.billing,
            urgency=UrgencyEnum.high,
            suggested_team=TeamEnum.finance,
            confidence=0.95,
            reason="Stub response: Customer reported a duplicate charge on their invoice.",
        )

    # Placeholder until Stage 2 wires the real model call
    raise HTTPException(
        status_code=501,
        detail="Model integration not wired yet. Set LLM_STUB=1 for Stage 1 testing.",
    )
