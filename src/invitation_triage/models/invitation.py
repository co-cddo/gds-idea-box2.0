from enum import Enum

from pydantic import BaseModel, Field


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
    """Email that is not an invitation requiring triage."""

    email_id: str = Field(
        description="Unique identifier linking back to the source email"
    )
    reason: str = Field(
        description="Brief explanation of why this is not an invitation (e.g., 'informational update', 'thank you note', 'forwarded document')"
    )


class Invitation(BaseModel):
    """Email that is an invitation requiring ministerial triage."""

    email_id: str = Field(
        description="Unique identifier linking back to the source email"
    )

    event_type: EventType = Field(description="Type of event being invited to")

    host_org: str = Field(description="Organization or individual hosting the event")

    purpose: str = Field(description="Stated purpose or description of the event")

    event_summary: str = Field(
        description="Concise 2-3 sentence summary of the event for quick review"
    )

    topics: list[str] = Field(
        description="Relevant policy topics from the minister's portfolio (DSIT/DESNZ taxonomy)"
    )

    proposed_times: list[str] = Field(
        description="Proposed date/time options as raw text (e.g., '15th February 2026, 6:00 PM', 'week of March 4')"
    )

    is_time_flexible: bool = Field(
        description="Whether multiple time options are offered or flexibility is mentioned"
    )

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
        description="LLM's confidence in extraction quality (0.0-1.0). 1.0 = very clear, 0.5 = some ambiguity, 0.2 = lots of guessing",
    )
