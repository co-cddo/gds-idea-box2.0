"""Schema for the SharePoint actions list."""

from typing import Literal

from pydantic import BaseModel, Field


class SharepointAction(BaseModel):
    """Schema for the SharePoint actions list.

    Each row represents a single actionable item extracted from a
    minister's review of a submission or invitation.
    """

    title: str = Field(description="Brief title for this action")

    action_id: str = Field(description="Unique identifier for this action")

    description: str = Field(
        min_length=10,
        description="Clear description of what needs to be done "
        "(e.g., 'Send acceptance email to Dr Sarah Chen', 'Add event to calendar')",
    )

    action_type: Literal[
        "correspondence",
        "calendar",
        "approval",
        "briefing",
        "meeting",
        "notification",
        "other",
    ] = Field(description="Type of action required")

    draft_content: str | None = Field(
        default=None,
        description="Final draft text for correspondence actions. Should be ready to send with minimal edits.",
    )

    deadline: str | None = Field(
        default=None,
        description="Deadline as stated in raw text (e.g., 'By 5th February 2026', 'Before the event', 'ASAP')",
    )

    urgency: Literal["urgent", "routine", "low"] = Field(
        default="routine",
        description="How urgent this action is",
    )

    owner: str | None = Field(
        default=None,
        description="Who should do this action (e.g., 'Private Office', 'AI Policy Team', 'Minister')",
    )

    status: Literal["pending", "in_progress", "completed"] = Field(
        default="pending",
        description="Current status of this action",
    )

    document_id: str = Field(description="Links back to the source document that generated this action")

    source_document_type: Literal["invitation", "submission"] = Field(
        description="Type of document this action was extracted from",
    )

    created_at: str = Field(description="When this action was created (ISO format)")

    document_type: Literal["invitation", "submission"] = Field(
        description="Type of document this action relates to",
    )

    office_decision: Literal["yes", "yes_but", "no"] = Field(
        description="The office's decision on behalf of the minister, inferred from their comment",
    )

    final_draft: str = Field(description="Minister's comment verbatim")

    summary: str = Field(
        min_length=20,
        description="Brief summary of the decision and key actions to be taken",
    )

    minister_comment: str = Field(
        description="Minister's comments on how to proceed",
    )
