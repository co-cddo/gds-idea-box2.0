from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class OfficeResponse(BaseModel):
    """Private Office's response on behalf of the minister to a document."""

    document_id: str = Field(
        description="Links back to the source document (invitation or submission)"
    )
    document_type: Literal["invitation", "submission"]

    decision: Literal["yes", "yes_but", "no"] = Field(
        description="Minister's decision: "
        "'yes' = approve/accept as recommended, "
        "'yes_but' = approve/accept with modifications, "
        "'no' = decline/reject"
    )

    notes: str | None = Field(
        default=None,
        description="Free text notes explaining modifications, conditions, or concerns. "
        "Required for 'yes_but' and 'no' decisions. "
        "(e.g., 'Can only attend from 7pm', 'Approve £2M not £3M', 'Need more detail on risks')",
    )

    responded_at: datetime = Field(
        default_factory=datetime.now,
        description="When this response was recorded",
    )

    responded_by: str = Field(
        default="Private Office",
        description="Who recorded this response (e.g., 'Private Office', staff name)",
    )


class Action(BaseModel):
    """A discrete actionable item extracted from the minister's response."""

    action_id: str = Field(
        default_factory=lambda: f"ACT-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')[:20]}",
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
        description="Final draft text for correspondence actions. "
        "Should be ready to send with minimal edits.",
    )

    # Timing and priority
    deadline: str | None = Field(
        default=None,
        description="Deadline as stated in raw text "
        "(e.g., 'By 5th February 2026', 'Before the event', 'ASAP')",
    )

    urgency: Literal["urgent", "routine", "low"] = Field(
        default="routine", description="How urgent this action is"
    )

    # Ownership
    owner: str | None = Field(
        default=None,
        description="Who should do this action "
        "(e.g., 'Private Office', 'AI Policy Team', 'Minister')",
    )

    # Status tracking
    status: Literal["pending", "in_progress", "completed"] = Field(
        default="pending", description="Current status of this action"
    )

    # Linking back to source
    source_document_id: str = Field(
        description="Links back to the source document that generated this action"
    )
    source_document_type: Literal["invitation", "submission"]

    # Audit trail
    created_at: datetime = Field(
        default_factory=datetime.now, description="When this action was created"
    )


class FinalDraft(BaseModel):
    """Final approved draft after potential redrafting."""

    document_id: str

    content: str = Field(
        min_length=50, description="Final draft text ready to send"
    )

    was_modified: bool = Field(
        description="True if the draft was redrafted based on office notes, "
        "False if using the original system-generated draft"
    )

    office_notes: str | None = Field(
        default=None,
        description="Office notes that informed the redraft (if was_modified=True)",
    )

    created_at: datetime = Field(
        default_factory=datetime.now, description="When this draft was finalized"
    )


class ActionExtractionResult(BaseModel):
    """Complete result of action extraction: final draft + extracted actions."""

    document_id: str
    document_type: Literal["invitation", "submission"]

    office_decision: Literal["yes", "yes_but", "no"] = Field(
        description="The office's decision on behalf of the minister"
    )

    final_draft: FinalDraft = Field(
        description="Final approved draft (original or redrafted)"
    )

    actions: list[Action] = Field(
        description="List of actionable items extracted from the decision"
    )

    summary: str = Field(
        min_length=20,
        description="Brief summary of the decision and key actions to be taken",
    )

    created_at: datetime = Field(
        default_factory=datetime.now,
        description="When this action extraction was performed",
    )
