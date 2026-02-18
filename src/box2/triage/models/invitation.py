from enum import Enum

from pydantic import BaseModel, Field, field_validator


class EventType(str, Enum):
    """Type of ministerial event."""

    MEETING = "meeting"
    SPEECH = "speech"
    PANEL = "panel"
    RECEPTION = "reception"
    SITE_VISIT = "site_visit"
    CONFERENCE = "conference"
    OTHER = "other"


class NotInvitation(BaseModel):
    """Document that is not an invitation requiring triage."""

    document_id: str = Field(description="Unique identifier linking back to the source document")
    reason: str = Field(
        min_length=10,
        description="Brief explanation of why this is not an invitation "
        "(e.g., 'informational update', 'thank you note', 'forwarded document')",
    )


class Invitation(BaseModel):
    """Document that is an invitation requiring ministerial triage."""

    document_id: str = Field(description="Unique identifier linking back to the source document")

    event_type: EventType = Field(description="Type of event being invited to")

    host_org: str = Field(description="Organization or individual hosting the event")

    purpose: str = Field(min_length=10, description="Stated purpose or description of the event")

    event_summary: str = Field(
        min_length=10,
        description="Concise 2-3 sentence summary of the event for quick review",
    )

    topics: list[str] = Field(description="Relevant policy topics from the minister's portfolio (DSIT/DESNZ taxonomy)")

    proposed_times: list[str] = Field(
        description="Proposed date/time options as raw text (e.g., '15th February 2026, 6:00 PM', 'week of March 4')"
    )

    is_time_flexible: bool = Field(description="Whether multiple time options are offered or flexibility is mentioned")

    location: str = Field(
        description="Event location as stated in email (e.g., 'The Royal Society, London' or 'Virtual via Zoom')"
    )

    deadline_to_respond: str | None = Field(
        default=None,
        description="Deadline for responding if mentioned (as raw text, e.g., '5th February 2026')",
    )

    overall_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="LLM's confidence in extraction quality (0.0-1.0). "
        "1.0 = very clear, 0.5 = some ambiguity, 0.2 = lots of guessing",
    )

    @field_validator("proposed_times")
    @classmethod
    def validate_proposed_times_not_empty(cls, v: list[str]) -> list[str]:
        """Ensure at least one proposed time is provided."""
        if not v or len(v) == 0:
            raise ValueError("proposed_times must contain at least one time option")
        return v
