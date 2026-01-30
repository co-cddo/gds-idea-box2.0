"""
Calendar interface for checking ministerial availability.

Mock implementation returns realistic calendar events for testing.
In production, this would integrate with Outlook/Google Calendar API.
"""

import logging
from datetime import datetime, timedelta
from typing import Protocol

from invitation_triage.exceptions import CalendarError
from invitation_triage.models import CalendarEvent

logger = logging.getLogger(__name__)


class CalendarProvider(Protocol):
    """Protocol defining the calendar interface."""

    def get_events(
        self, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """
        Get all events in the specified date range.

        Args:
            start_date: Start of range (inclusive)
            end_date: End of range (inclusive)

        Returns:
            List of CalendarEvent instances
        """
        ...


class MockCalendar:
    """
    Mock calendar implementation with realistic ministerial schedule.

    Returns plausible events for testing the decision logic.
    """

    def __init__(self):
        """Initialize with a set of recurring/typical events."""
        # This could be loaded from a JSON file in real implementation
        self._base_events = self._generate_typical_schedule()

    def get_events(
        self, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """
        Get mock events in the date range.

        Args:
            start_date: Start of range
            end_date: End of range

        Returns:
            List of CalendarEvent instances that overlap with the range
        """
        events = []

        # Add recurring weekly events
        current = start_date
        while current <= end_date:
            weekday = current.strftime("%A")
            events.extend(self._get_events_for_day(current, weekday))
            current += timedelta(days=1)

        # Add some specific dated events
        events.extend(self._get_specific_events(start_date, end_date))

        return events

    def _get_events_for_day(self, date: datetime, weekday: str) -> list[CalendarEvent]:
        """Get recurring events for a specific day of week."""
        events = []
        date_str = date.strftime("%Y-%m-%d")

        if weekday == "Monday":
            events.extend(
                [
                    CalendarEvent(
                        title="Ministerial Team Meeting",
                        start_time=f"{date_str} 09:00",
                        end_time=f"{date_str} 10:00",
                        description="Weekly team sync",
                        priority="high",
                    ),
                    CalendarEvent(
                        title="Department Brief - DSIT",
                        start_time=f"{date_str} 14:00",
                        end_time=f"{date_str} 15:00",
                        priority="high",
                    ),
                ]
            )

        elif weekday == "Tuesday":
            events.append(
                CalendarEvent(
                    title="Parliamentary Questions Prep",
                    start_time=f"{date_str} 10:00",
                    end_time=f"{date_str} 11:30",
                    priority="high",
                )
            )

        elif weekday == "Wednesday":
            events.append(
                CalendarEvent(
                    title="PMQs and Parliamentary Business",
                    start_time=f"{date_str} 11:30",
                    end_time=f"{date_str} 14:30",
                    description="Wednesday parliamentary schedule",
                    priority="high",
                )
            )

        elif weekday == "Thursday":
            events.append(
                CalendarEvent(
                    title="Constituency Engagement",
                    start_time=f"{date_str} 14:00",
                    end_time=f"{date_str} 17:00",
                    description="Regular constituency time",
                    priority="medium",
                )
            )

        elif weekday == "Friday":
            # Lighter Friday schedule
            events.append(
                CalendarEvent(
                    title="Constituency Office Hours",
                    start_time=f"{date_str} 10:00",
                    end_time=f"{date_str} 16:00",
                    description="In constituency",
                    priority="medium",
                )
            )

        return events

    def _get_specific_events(
        self, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Get specific one-off events in the date range."""
        # Some realistic specific events
        specific_events = [
            CalendarEvent(
                title="Cabinet Committee - Science and Technology",
                start_time=datetime(
                    2026, 2, 10, 10, 0
                ),  # Change from string to datetime
                end_time=datetime(2026, 2, 10, 12, 0),  # Change from string to datetime
                description="Monthly Cabinet subcommittee",
                priority="high",
            ),
            CalendarEvent(
                title="Meeting with Secretary of State",
                start_time=datetime(2026, 2, 15, 15, 0),
                end_time=datetime(2026, 2, 15, 16, 0),
                priority="high",
            ),
            CalendarEvent(
                title="Visit to Imperial College AI Lab",
                start_time=datetime(2026, 2, 20, 14, 0),
                end_time=datetime(2026, 2, 20, 17, 0),
                description="Pre-scheduled lab visit",
                priority="medium",
            ),
            CalendarEvent(
                title="Budget Discussions - DSIT",
                start_time=datetime(2026, 3, 5, 9, 0),
                end_time=datetime(2026, 3, 5, 17, 0),
                description="Full day budget planning",
                priority="high",
            ),
            CalendarEvent(
                title="International Partners Reception",
                start_time=datetime(2026, 3, 11, 18, 0),
                end_time=datetime(2026, 3, 11, 20, 0),
                description="Evening reception with international delegations",
                priority="medium",
            ),
        ]

        # Filter to date range - now comparing datetime objects directly
        return [
            event
            for event in specific_events
            if start_date <= event.start_time <= end_date
        ]

    def _generate_typical_schedule(self) -> dict:
        """Generate typical recurring events (for future use)."""
        return {}


# ============================================================================
# Interface functions
# ============================================================================


def get_calendar_events(
    start_date: datetime, end_date: datetime, provider: CalendarProvider | None = None
) -> list[CalendarEvent]:
    """
    Get calendar events for a date range.

    Args:
        start_date: Start of range
        end_date: End of range
        provider: Calendar provider instance (uses MockCalendar if None)

    Returns:
        List of CalendarEvent instances

    Raises:
        CalendarError: If date range is invalid or provider fails

    Note:
        In production, replace MockCalendar with:
        - OutlookCalendar(credentials)
        - GoogleCalendar(credentials)
        - CalendarAPIClient(api_key)
    """
    # Validate date range
    if start_date > end_date:
        logger.error(
            f"Invalid date range: start ({start_date}) > end ({end_date})"
        )
        raise CalendarError(
            f"Invalid date range: start_date ({start_date}) "
            f"must be <= end_date ({end_date})"
        )

    if provider is None:
        provider = MockCalendar()

    logger.debug(
        f"Querying calendar: {start_date} to {end_date}",
        extra={
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "provider": type(provider).__name__,
        },
    )

    try:
        events = provider.get_events(start_date, end_date)
        logger.info(
            f"Retrieved {len(events)} calendar events",
            extra={"event_count": len(events)},
        )
        return events
    except Exception as e:
        logger.error(
            f"Calendar provider failed: {str(e)}",
            exc_info=True,
        )
        # Wrap provider exceptions in CalendarError
        raise CalendarError(
            f"Calendar provider failed to retrieve events: {str(e)}",
            cause=e,
        ) from e
