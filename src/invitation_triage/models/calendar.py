"""
Calendar event models.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


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

    location: str | None = Field(
        default=None, description="Event location or 'Virtual' for online meetings"
    )

    priority: Literal["high", "medium", "low"] = Field(
        description="Importance/priority level of this event"
    )

    description: str | None = Field(
        default=None, description="Additional details about the event"
    )
