"""Result models for the file triage pipeline."""

from pydantic import BaseModel, Field

from box2.triage.models import Invitation, TriagedDecision


class TriagedInvitation(BaseModel):
    """An invitation that has been extracted and triaged.

    Pairs the extracted invitation details with the triage decision
    (recommended action, priority, draft response, calendar conflicts).
    """

    invitation: Invitation = Field(description="Extracted invitation details")
    decision: TriagedDecision = Field(description="Triage recommendation and draft response")
