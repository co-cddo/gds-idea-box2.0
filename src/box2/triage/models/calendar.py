"""
Calendar event models.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class CalendarEvent(BaseModel):
    """
    An event already scheduled on the minister's calendar.

    Used to detect conflicts and assess relative priority of competing commitments.

    Possible expansions
    - event_type: Classification of event (parliamentary, meeting, travel, etc.)
    - is_movable: Whether event can be rescheduled
    - attendees: List of other participants
    - recurrence: For recurring events
    """

    title: str = Field(description="Event title/description")

    start_time: datetime = Field(description="Event start date and time")

    end_time: datetime = Field(description="Event end date and time")

    location: str | None = Field(default=None, description="Event location or 'Virtual' for online meetings")

    priority: Literal["high", "medium", "low"] = Field(description="Importance/priority level of this event")

    description: str | None = Field(default=None, description="Additional details about the event")

    @model_validator(mode="after")
    def validate_time_range(self) -> "CalendarEvent":
        """Ensure start_time is before end_time."""
        if self.start_time >= self.end_time:
            raise ValueError(f"start_time ({self.start_time}) must be before end_time ({self.end_time})")
        return self
