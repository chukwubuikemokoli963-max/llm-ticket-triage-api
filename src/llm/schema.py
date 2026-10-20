from enum import Enum
from pydantic import BaseModel, Field, ConfigDict

class CategoryEnum(str, Enum):
    billing = "billing"
    technical = "technical"
    account = "account"
    feature_request = "feature_request"
    other = "other"

class UrgencyEnum(str, Enum):
    low = "low"
    normal = "normal"
    high = "high"

class TeamEnum(str, Enum):
    finance = "finance"
    engineering = "engineering"
    support = "support"
    product = "product"
    triage = "triage"

class TriageInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    text: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The incoming customer support ticket or complaint text (1-2000 chars).",
    )


class TriageOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: CategoryEnum
    urgency: UrgencyEnum
    suggested_team: TeamEnum
    confidence: float = Field(..., ge=0.0, le=1.0)
    reason: str = Field(..., min_length=1, max_length=300)
