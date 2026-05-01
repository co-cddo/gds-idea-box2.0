"""Schema for the SharePoint actions list."""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class ActionStatus(str, Enum):
    """Action status to be changed by private office staff. Defalts to pending."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class SharepointAction(BaseModel):
    """A discrete actionable item extracted from the minister's response."""

    action_id: str = Field(
        description="Unique identifier for this action",
    )

    description: str = Field(
        min_length=10,
        description="Clear description of what needs to be done "
        "(e.g., 'Send acceptance email to Dr Sarah Chen', 'Add event to calendar')",
    )

    action_type: Literal[
        "correspondence",  # Send email/letter/memo
        "calendar",  # Add to minister's calendar
        "approval",  # Sign/approve document
        "briefing",  # Prepare briefing materials
        "meeting",  # Arrange meeting
        "notification",  # Notify stakeholder
        "other",  # Other actions
    ] = Field(description="Type of action required")

    # For correspondence actions - include the final draft
    draft_content: str | None = Field(
        default=None,
        description="Final draft text for correspondence actions. Should be ready to send with minimal edits.",
    )

    calendar_conflicts: str | None = Field(
        default=None,
        description="Calendar events that conflict with this invitation, identified during triage (e.g. 'Cabinet committee 15 Feb 6-7pm",
    )

    # Timing and priority
    deadline: str | None = Field(
        default=None,
        description="Deadline as stated in raw text (e.g., 'By 5th February 2026', 'Before the event', 'ASAP')",
    )

    urgency: Literal["urgent", "routine", "low"] = Field(default="routine", description="How urgent this action is")

    # Ownership
    owner: str | None = Field(
        default=None,
        description="Who should do this action (e.g., 'Private Office', 'AI Policy Team', 'Minister')",
    )

    # Status tracking
    status: ActionStatus = Field(default="pending", description="Current status of this action")

    # Linking back to source
    document_id: str = Field(description="Links back to the source document that generated this action")
    source_document_type: Literal["invitation", "submission"]

    # Audit trail
    created_at: str = Field(description="When this action was created")

    document_type: Literal["invitation", "submission"]

    office_decision: Literal["yes", "yes_but", "no"] = Field(
        description="The office's decision on behalf of the minister"
    )

    final_draft: str = Field(description="Final approved draft (original or redrafted)")

    title: str = Field(description="List of actionable items extracted from the decision")

    summary: str = Field(
        min_length=20,
        description="Brief summary of the decision and key actions to be taken",
    )

    minister_comment: str = Field(description="Minister's comments on how to proceed with the action")

    action_progress: Literal["yes", "yes_but", "no"] = Field(
        description="The office's decision on behalf of the minister"
    )
