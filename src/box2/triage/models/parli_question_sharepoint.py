from datetime import date, datetime
from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, Field


class SharepointPQs(BaseModel):
    """Schema for the Sharepoint parliamentary questions list"""

    # --- Parliament API fields (always present) ---

    title: str = Field(description="UIN — unique identifier for PQ")

    questiontext: str = Field(description="Parliamentary question")

    house: Literal["commons", "lords"] = Field(description="House that tabled the PQ")

    datetabled: datetime = Field(description="Date the PQ was tabled")

    date_for_answer: datetime = Field(description="Date by which the PQ must be answered")

    asking_member_id: str = Field(description="ID of member of parliament asking the PQ")

    answering_body_name: str = Field(description="Name of department answering the PQ")

    is_named_day: bool = Field(
        description="Parliamentary question that the Government are required to answer on a specific date"
    )

    asking_member_name: str = Field(description="Name of member of parliament asking the PQ")

    # --- AI-generated fields (may be None if pipeline stage fails) ---

    responding_minister: str | None = Field(
        default=None, description="Responding minister based on house (commons/lords). House always takes precedent"
    )

    policy_minister: str | None = Field(
        default=None,
        description="Responding minister based on area of expertise. If it's a lords PQ however, this takes precedent and will always be answered by a lord minister",
    )

    ai_expansive_answer: str | None = Field(default=None, description="Detailed LLM draft response")

    ai_generic_answer: str | None = Field(default=None, description="Generic LLM draft response")

    url: list[AnyHttpUrl] = Field(default_factory=list, description="List of links used by LLM for draft response")

    ai_predicted_directorate: str | None = Field(default=None, description="Predicted directorate")

    ai_predicted_scs: str | None = Field(default=None, description="Predicted SCS")

    ai_routing_confidence: str | None = Field(default=None, description="Predicted confidence")

    ai_routing_reasoning: str | None = Field(default=None, description="Predicted reasoning")

    ai_routing_alternative_directorate: str | None = Field(
        default=None, description="Predicted alternative directorate"
    )

    # --- Computed fields ---

    urgency: Literal["urgent", "not urgent"] = Field(
        description="Urgency for the minister to review draft response. Urgent responses <=2 days before dateforAnswer"
    )

    target_date: date = Field(description="Calculated date for parliamentary unit from date_for_answer")

    draft_due: date = Field(description="Calculated date ")

    spads: Literal["With Spads", "Spads", "Uncontroversial"] = Field(description="Spads clearance status")

    officials: Literal["With Officials", "Officials Sent", "Officials"] = Field(
        description="Officials clearance status"
    )

    notes: str | None = Field(description="Additional notes")

    # --- Minister review fields (populated after human review) ---

    minister_comment: str | None = Field(
        default=None, description="Minister's additional feedback for his decision to approve/request redraft"
    )

    minister_decision: Literal["approve", "request redraft"] | None = Field(
        default=None, description="Minister decision on drafted response quality"
    )
