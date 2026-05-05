"""Result models for the file triage pipeline."""

from typing import Literal

from pydantic import BaseModel, Field

from box2.triage.models import Action, Invitation, TriagedDecision


class TriagedInvitation(BaseModel):
    """An invitation that has been extracted and triaged.

    Pairs the extracted invitation details with the triage decision
    (recommended action, priority, draft response, calendar conflicts).
    """

    invitation: Invitation = Field(description="Extracted invitation details")
    decision: TriagedDecision = Field(description="Triage recommendation and draft response")


class ActionReviewResult(BaseModel):
    """Result of extracting actions from a minister's review of a list item.

    Returned by :func:`extract_actions_from_review`. The LLM infers the
    office decision from the minister's comment, extracts discrete actions,
    and generates a brief summary.
    """

    actions: list[Action] = Field(description="Discrete actionable items extracted from the review")
    office_decision: Literal["yes", "yes_but", "no"] | None = Field(
        default=None, description="The office's decision inferred from the minister's comment"
    )
    summary: str = Field(
        min_length=20,
        description="Brief summary of the decision and key actions to be taken",
    )
