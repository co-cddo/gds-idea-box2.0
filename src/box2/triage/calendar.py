"""
Calendar interface for checking ministerial availability.

Mock implementation returns realistic calendar events for testing.
In production, this would integrate with Outlook/Google Calendar API.
"""

import logging
from datetime import datetime, timedelta
from typing import Protocol

from box2.triage.exceptions import CalendarError
from box2.triage.models import CalendarEvent

logger = logging.getLogger(__name__)


class CalendarProvider(Protocol):
    """Protocol defining the calendar interface."""

    def get_events(self, start_date: datetime, end_date: datetime) -> list[CalendarEvent]:
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

    Returns plausible events based on a two-week repeating template.
    The template cycles indefinitely - the minister lives in a Groundhog Day
    style two-week loop of science policy meetings.

    Note: PO (Private Office) briefings only occur on Monday mornings.
    """

    # Base date for the two-week cycle (Monday, Feb 2, 2026)
    CYCLE_START = datetime(2026, 2, 2)
    CYCLE_LENGTH_DAYS = 14

    def __init__(self):
        """Initialize with the two-week template schedule."""
        self._template = self._build_template()

    def get_events(self, start_date: datetime, end_date: datetime) -> list[CalendarEvent]:
        """
        Get mock events in the date range.

        Args:
            start_date: Start of range
            end_date: End of range

        Returns:
            List of CalendarEvent instances that overlap with the range
        """
        events = []

        current = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)

        while current <= end:
            events.extend(self._get_events_for_date(current))
            current += timedelta(days=1)

        return events

    def _get_events_for_date(self, date: datetime) -> list[CalendarEvent]:
        """
        Get events for a specific date by mapping to the two-week template.

        Args:
            date: The date to get events for

        Returns:
            List of CalendarEvent instances for that date
        """
        # Calculate days since cycle start
        days_since_start = (date - self.CYCLE_START).days

        # Map to position in 14-day cycle
        cycle_day = days_since_start % self.CYCLE_LENGTH_DAYS

        # Get template events for this cycle day
        template_events = self._template.get(cycle_day, [])

        # Create CalendarEvent instances with the requested date
        events = []
        for template in template_events:
            # Parse the template times and apply to requested date
            start_time = datetime.strptime(template["start_time"], "%Y-%m-%d %H:%M")
            end_time = datetime.strptime(template["end_time"], "%Y-%m-%d %H:%M")

            # Replace date components while keeping time
            event_start = date.replace(hour=start_time.hour, minute=start_time.minute, second=0, microsecond=0)
            event_end = date.replace(hour=end_time.hour, minute=end_time.minute, second=0, microsecond=0)

            events.append(
                CalendarEvent(
                    title=template["title"],
                    start_time=event_start,
                    end_time=event_end,
                    description=template["description"],
                    priority=template["priority"],
                    location=template["location"],
                )
            )

        return events

    def _build_template(self) -> dict[int, list[dict]]:
        """
        Build the two-week template schedule.

        Returns a dict mapping cycle_day (0-13) to list of event templates.
        Weekends (days 5-6, 12-13) are empty.

        Template structure matches realistic ministerial calendar focusing on:
        - Science and technology policy
        - Research funding (UKRI, ARIA, Horizon Europe)
        - Innovation programs (quantum, life sciences, engineering biology)
        - Regional development (Oxford-Cambridge corridor)
        - International collaboration
        """
        return {
            # ===== WEEK 1 =====
            # Day 0: Monday, Feb 2
            0: [
                {
                    "title": "PO morning briefing — day plan and priorities",
                    "start_time": "2026-02-02 08:30",
                    "end_time": "2026-02-02 09:00",
                    "description": "Set the day's plan, key messages, and urgent items.",
                    "priority": "high",
                    "location": "Ministerial Office",
                },
                {
                    "title": "Horizon Europe — position overview",
                    "start_time": "2026-02-02 09:15",
                    "end_time": "2026-02-02 10:00",
                    "description": "Receive an update on current context and agree near-term approach.",
                    "priority": "high",
                    "location": "Conference Room A, 1 Victoria Street",
                },
                {
                    "title": "Domestic research system — PSREs overview",
                    "start_time": "2026-02-02 10:15",
                    "end_time": "2026-02-02 11:00",
                    "description": "High-level stocktake on capability, estates, and coordination.",
                    "priority": "medium",
                    "location": "Conference Room A, 1 Victoria Street",
                },
                {
                    "title": "Quantum programme — delivery check-in",
                    "start_time": "2026-02-02 11:15",
                    "end_time": "2026-02-02 12:00",
                    "description": "Progress review and upcoming decisions.",
                    "priority": "medium",
                    "location": "Virtual",
                },
                {
                    "title": "Working lunch — Oxford–Cambridge Growth Corridor",
                    "start_time": "2026-02-02 12:15",
                    "end_time": "2026-02-02 13:00",
                    "description": "Discuss labs, planning interfaces, and growth narrative.",
                    "priority": "medium",
                    "location": "Ministerial Dining Room",
                },
                {
                    "title": "ARIA — portfolio and governance update",
                    "start_time": "2026-02-02 15:15",
                    "end_time": "2026-02-02 16:00",
                    "description": "Review portfolio balance, risk appetite, and reporting cadence.",
                    "priority": "medium",
                    "location": "Meeting Room B, 1 Victoria Street",
                },
            ],
            # Day 1: Tuesday, Feb 3
            1: [
                {
                    "title": "Life sciences — partnership session",
                    "start_time": "2026-02-03 09:00",
                    "end_time": "2026-02-03 09:45",
                    "description": "Discuss manufacturing, trials interface, and investment signals.",
                    "priority": "high",
                    "location": "Conference Room A, 1 Victoria Street",
                },
                {
                    "title": "GOTT — commercialisation pathways",
                    "start_time": "2026-02-03 10:00",
                    "end_time": "2026-02-03 10:45",
                    "description": "Overview of bottlenecks, IP models, and options to improve flow.",
                    "priority": "medium",
                    "location": "Meeting Room B, 1 Victoria Street",
                },
                {
                    "title": "Regulatory Innovation Office — pipeline review",
                    "start_time": "2026-02-03 11:00",
                    "end_time": "2026-02-03 11:45",
                    "description": "Check status of sandboxes and agree success measures.",
                    "priority": "medium",
                    "location": "Virtual",
                },
                {
                    "title": "International space science — bilateral preparation",
                    "start_time": "2026-02-03 12:00",
                    "end_time": "2026-02-03 12:45",
                    "description": "Run through themes, data-sharing, and engagement lines.",
                    "priority": "medium",
                    "location": "Meeting Room C, 1 Victoria Street",
                },
                {
                    "title": "UKRI ecosystem — allocations framework",
                    "start_time": "2026-02-03 14:00",
                    "end_time": "2026-02-03 15:00",
                    "description": "Consider balance of discovery, mission-led work, and infrastructure.",
                    "priority": "high",
                    "location": "Conference Room A, 1 Victoria Street",
                },
                {
                    "title": "Tech & innovation across missions — dashboard",
                    "start_time": "2026-02-03 15:15",
                    "end_time": "2026-02-03 16:00",
                    "description": "Review delivery indicators and interdependencies.",
                    "priority": "medium",
                    "location": "Virtual",
                },
            ],
            # Day 2: Wednesday, Feb 4
            2: [
                {
                    "title": "R&D environment — policy review",
                    "start_time": "2026-02-04 08:45",
                    "end_time": "2026-02-04 09:30",
                    "description": "Test incentive options and alignment with growth aims.",
                    "priority": "high",
                    "location": "Ministerial Office",
                },
                {
                    "title": "Engineering biology — programme update",
                    "start_time": "2026-02-04 09:45",
                    "end_time": "2026-02-04 10:30",
                    "description": "Check pipeline health, standards work, and testbeds.",
                    "priority": "medium",
                    "location": "Conference Room A, 1 Victoria Street",
                },
                {
                    "title": "Oxford–Cambridge Corridor — planning interfaces",
                    "start_time": "2026-02-04 10:45",
                    "end_time": "2026-02-04 11:30",
                    "description": "Discuss sites, utilities, and skills with relevant bodies (fictional).",
                    "priority": "medium",
                    "location": "Virtual",
                },
                {
                    "title": "International R&D — MoU pipeline",
                    "start_time": "2026-02-04 11:45",
                    "end_time": "2026-02-04 12:30",
                    "description": "Prioritise themes and sequencing for cooperation.",
                    "priority": "medium",
                    "location": "Meeting Room B, 1 Victoria Street",
                },
                {
                    "title": "Quantum and compute — capability session",
                    "start_time": "2026-02-04 14:00",
                    "end_time": "2026-02-04 14:45",
                    "description": "Consider capability intersections and workforce needs.",
                    "priority": "medium",
                    "location": "Virtual",
                },
                {
                    "title": "Speech preparation — science-led growth",
                    "start_time": "2026-02-04 15:00",
                    "end_time": "2026-02-04 16:00",
                    "description": "Refine narrative and supporting examples.",
                    "priority": "medium",
                    "location": "Ministerial Office",
                },
            ],
            # Day 3: Thursday, Feb 5
            3: [
                {
                    "title": "PSRE reform — programme checkpoint",
                    "start_time": "2026-02-05 09:00",
                    "end_time": "2026-02-05 09:45",
                    "description": "Confirm scope, milestones, and options.",
                    "priority": "high",
                    "location": "Conference Room A, 1 Victoria Street",
                },
                {
                    "title": "Horizon Europe — comms planning",
                    "start_time": "2026-02-05 10:00",
                    "end_time": "2026-02-05 10:45",
                    "description": "Agree stakeholder touchpoints and messages.",
                    "priority": "medium",
                    "location": "Meeting Room B, 1 Victoria Street",
                },
                {
                    "title": "ARIA oversight — risk and assurance",
                    "start_time": "2026-02-05 15:00",
                    "end_time": "2026-02-05 16:00",
                    "description": "Deep-dive on challenge processes and portfolio balance.",
                    "priority": "high",
                    "location": "Conference Room A, 1 Victoria Street",
                },
            ],
            # Day 4: Friday, Feb 6
            4: [
                {
                    "title": "Life sciences — manufacturing scale-up",
                    "start_time": "2026-02-06 09:00",
                    "end_time": "2026-02-06 09:45",
                    "description": "Review facilities pipeline and export potential.",
                    "priority": "high",
                    "location": "Conference Room A, 1 Victoria Street",
                },
                {
                    "title": "GOTT — IP and revenue strategy",
                    "start_time": "2026-02-06 10:00",
                    "end_time": "2026-02-06 10:45",
                    "description": "Consider licensing, equity, and recycling options.",
                    "priority": "medium",
                    "location": "Meeting Room B, 1 Victoria Street",
                },
                {
                    "title": "Regulatory sandbox — next approvals",
                    "start_time": "2026-02-06 11:00",
                    "end_time": "2026-02-06 11:45",
                    "description": "Confirm criteria and evaluation plan.",
                    "priority": "medium",
                    "location": "Virtual",
                },
                {
                    "title": "UKRI engagement — board preparation",
                    "start_time": "2026-02-06 12:00",
                    "end_time": "2026-02-06 12:45",
                    "description": "Run through principles and expected questions.",
                    "priority": "medium",
                    "location": "Meeting Room C, 1 Victoria Street",
                },
                {
                    "title": "Quantum missions — delivery risks",
                    "start_time": "2026-02-06 14:00",
                    "end_time": "2026-02-06 14:45",
                    "description": "Discuss dependencies and mitigations.",
                    "priority": "high",
                    "location": "Virtual",
                },
                {
                    "title": "Evidence & data — R&D indicators",
                    "start_time": "2026-02-06 15:00",
                    "end_time": "2026-02-06 15:45",
                    "description": "Walk through key statistics and regional picture.",
                    "priority": "medium",
                    "location": "Virtual",
                },
            ],
            # Days 5-6: Weekend (empty)
            5: [],
            6: [],
            # ===== WEEK 2 =====
            # Day 7: Monday, Feb 9
            7: [
                {
                    "title": "PO morning briefing — day plan and priorities",
                    "start_time": "2026-02-09 08:30",
                    "end_time": "2026-02-09 09:00",
                    "description": "Confirm schedule, key messages, and urgent items.",
                    "priority": "high",
                    "location": "Ministerial Office",
                },
                {
                    "title": "Horizon Europe — scenario discussion",
                    "start_time": "2026-02-09 09:15",
                    "end_time": "2026-02-09 10:00",
                    "description": "Review options and agree engagement posture.",
                    "priority": "high",
                    "location": "Conference Room A, 1 Victoria Street",
                },
                {
                    "title": "Space science — council agenda run-through",
                    "start_time": "2026-02-09 10:15",
                    "end_time": "2026-02-09 11:00",
                    "description": "Mock agenda: missions, data policy, and skills.",
                    "priority": "medium",
                    "location": "Virtual",
                },
                {
                    "title": "Engineering biology — roadmap and standards",
                    "start_time": "2026-02-09 11:15",
                    "end_time": "2026-02-09 12:00",
                    "description": "Align roadmap with regulatory pathways and testbeds.",
                    "priority": "medium",
                    "location": "Conference Room A, 1 Victoria Street",
                },
                {
                    "title": "Working lunch — Oxford–Cambridge labs & housing",
                    "start_time": "2026-02-09 12:15",
                    "end_time": "2026-02-09 13:00",
                    "description": "Discuss growth, affordability, and infrastructure.",
                    "priority": "medium",
                    "location": "Ministerial Dining Room",
                },
                {
                    "title": "Regulatory Innovation Office — metrics and cadence",
                    "start_time": "2026-02-09 14:00",
                    "end_time": "2026-02-09 15:00",
                    "description": "Agree measures for speed, clarity, and safety.",
                    "priority": "medium",
                    "location": "Meeting Room B, 1 Victoria Street",
                },
                {
                    "title": "ARIA pipeline — go/no-go gates",
                    "start_time": "2026-02-09 15:15",
                    "end_time": "2026-02-09 16:00",
                    "description": "Confirm gating criteria and oversight rhythm.",
                    "priority": "high",
                    "location": "Conference Room A, 1 Victoria Street",
                },
            ],
            # Day 8: Tuesday, Feb 10
            8: [
                {
                    "title": "UKRI allocations — fiscal choices",
                    "start_time": "2026-02-10 09:00",
                    "end_time": "2026-02-10 09:45",
                    "description": "Balance discovery, infrastructure, and mission-led activity.",
                    "priority": "high",
                    "location": "Conference Room A, 1 Victoria Street",
                },
                {
                    "title": "Life sciences — NHS interface",
                    "start_time": "2026-02-10 10:00",
                    "end_time": "2026-02-10 10:45",
                    "description": "Focus on set-up times, data, and site capacity.",
                    "priority": "medium",
                    "location": "Virtual",
                },
                {
                    "title": "Quantum — skills and talent",
                    "start_time": "2026-02-10 11:00",
                    "end_time": "2026-02-10 11:45",
                    "description": "Discuss training routes and placements.",
                    "priority": "medium",
                    "location": "Meeting Room B, 1 Victoria Street",
                },
                {
                    "title": "GOTT — case studies",
                    "start_time": "2026-02-10 12:00",
                    "end_time": "2026-02-10 12:45",
                    "description": "Fictional exemplars on licensing and spin-outs.",
                    "priority": "medium",
                    "location": "Virtual",
                },
                {
                    "title": "International collaboration — Indo-Pacific focus",
                    "start_time": "2026-02-10 14:00",
                    "end_time": "2026-02-10 15:00",
                    "description": "Set thematic focus and next steps.",
                    "priority": "high",
                    "location": "Conference Room A, 1 Victoria Street",
                },
                {
                    "title": "Missions delivery board — interlocks",
                    "start_time": "2026-02-10 15:15",
                    "end_time": "2026-02-10 16:00",
                    "description": "Consolidate risks, actions, and owners.",
                    "priority": "medium",
                    "location": "Meeting Room C, 1 Victoria Street",
                },
            ],
            # Day 9: Wednesday, Feb 11
            9: [
                {
                    "title": "Advanced Materials — investment climate roundtable",
                    "start_time": "2026-02-11 08:45",
                    "end_time": "2026-02-11 09:30",
                    "description": "Discuss design strengths, access, and capital needs.",
                    "priority": "high",
                    "location": "Conference Room A, 1 Victoria Street",
                },
                {
                    "title": "PSRE estate — capability mapping",
                    "start_time": "2026-02-11 09:45",
                    "end_time": "2026-02-11 10:30",
                    "description": "Review estate pressures and collaboration models.",
                    "priority": "medium",
                    "location": "Virtual",
                },
                {
                    "title": "Place-based R&D — clusters and devolution",
                    "start_time": "2026-02-11 10:45",
                    "end_time": "2026-02-11 11:30",
                    "description": "Align funding tools with local growth aims.",
                    "priority": "medium",
                    "location": "Meeting Room B, 1 Victoria Street",
                },
                {
                    "title": "AI & science interface — policy steer",
                    "start_time": "2026-02-11 11:45",
                    "end_time": "2026-02-11 12:30",
                    "description": "Coordinate research priorities and standards.",
                    "priority": "medium",
                    "location": "Conference Room A, 1 Victoria Street",
                },
                {
                    "title": "Horizon Europe — sector briefings",
                    "start_time": "2026-02-11 14:00",
                    "end_time": "2026-02-11 14:45",
                    "description": "Plan targeted briefings for academia and industry (fictional).",
                    "priority": "medium",
                    "location": "Virtual",
                },
                {
                    "title": "Parliamentary Q&A preparation — science portfolio",
                    "start_time": "2026-02-11 15:00",
                    "end_time": "2026-02-11 15:45",
                    "description": "Run through pack, figures, and examples.",
                    "priority": "medium",
                    "location": "Ministerial Office",
                },
            ],
            # Day 10: Thursday, Feb 12
            10: [
                {
                    "title": "ARIA — risk appetite and balance",
                    "start_time": "2026-02-12 10:00",
                    "end_time": "2026-02-12 10:45",
                    "description": "Discuss boldness, assurance, and challenge.",
                    "priority": "high",
                    "location": "Conference Room A, 1 Victoria Street",
                },
                {
                    "title": "Engineering biology — standards alignment",
                    "start_time": "2026-02-12 11:00",
                    "end_time": "2026-02-12 11:45",
                    "description": "Coordinate with relevant standards bodies.",
                    "priority": "medium",
                    "location": "Virtual",
                },
                {
                    "title": "Regulatory innovation — cross-Whitehall coordination",
                    "start_time": "2026-02-12 14:00",
                    "end_time": "2026-02-12 14:45",
                    "description": "Synchronise timelines, evaluation, and engagement.",
                    "priority": "medium",
                    "location": "Meeting Room B, 1 Victoria Street",
                },
                {
                    "title": "Oxford–Cambridge — digital connectivity plan",
                    "start_time": "2026-02-12 15:00",
                    "end_time": "2026-02-12 16:00",
                    "description": "Map connectivity priorities to lab growth.",
                    "priority": "medium",
                    "location": "Virtual",
                },
            ],
            # Day 11: Friday, Feb 13
            11: [
                {
                    "title": "Life sciences — investment roundtable",
                    "start_time": "2026-02-13 09:00",
                    "end_time": "2026-02-13 09:45",
                    "description": "Discuss scale-up finance and regulatory predictability.",
                    "priority": "high",
                    "location": "Conference Room A, 1 Victoria Street",
                },
                {
                    "title": "Quantum programme finance — approvals timetable",
                    "start_time": "2026-02-13 10:00",
                    "end_time": "2026-02-13 10:45",
                    "description": "Walk through spend, gates, and sequencing.",
                    "priority": "high",
                    "location": "Meeting Room B, 1 Victoria Street",
                },
                {
                    "title": "GOTT governance — performance framework",
                    "start_time": "2026-02-13 11:00",
                    "end_time": "2026-02-13 11:45",
                    "description": "Agree KPIs and reporting cadence.",
                    "priority": "medium",
                    "location": "Virtual",
                },
                {
                    "title": "International R&D mobility — talent",
                    "start_time": "2026-02-13 12:00",
                    "end_time": "2026-02-13 12:45",
                    "description": "Options for attraction and mobility within the ecosystem.",
                    "priority": "medium",
                    "location": "Meeting Room C, 1 Victoria Street",
                },
                {
                    "title": "Tech missions — outcomes and KPIs",
                    "start_time": "2026-02-13 14:00",
                    "end_time": "2026-02-13 14:45",
                    "description": "Consolidate metrics and delivery ownership.",
                    "priority": "medium",
                    "location": "Virtual",
                },
            ],
            # Days 12-13: Weekend (empty)
            12: [],
            13: [],
        }


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
        logger.error(f"Invalid date range: start ({start_date}) > end ({end_date})")
        raise CalendarError(f"Invalid date range: start_date ({start_date}) must be <= end_date ({end_date})")

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
