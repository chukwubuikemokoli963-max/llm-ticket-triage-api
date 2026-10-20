import os
from fastapi import APIRouter
from fastapi.responses import JSONResponse, PlainTextResponse
from src.llm.schema import TriageInput, TriageOutput, CategoryEnum, UrgencyEnum, TeamEnum
from src.llm.client import call_triage_model

router = APIRouter()


@router.post("/triage")
async def triage_ticket(payload: TriageInput):
    # Stage 1 Stub Mode
    if os.environ.get("LLM_STUB") == "1":
        stub_out = TriageOutput(
            category=CategoryEnum.billing,
            urgency=UrgencyEnum.high,
            suggested_team=TeamEnum.finance,
            confidence=0.95,
            reason="Stub response: Customer reported a duplicate charge on their invoice.",
        )
        return JSONResponse(status_code=200, content=stub_out.model_dump(mode="json"))

    # Stage 2: Load prompt file, call model, and return raw answer for visual inspection
    raw_answer = call_triage_model(payload.text)
    return PlainTextResponse(status_code=200, content=raw_answer)
