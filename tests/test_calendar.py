from datetime import datetime, timedelta

import pytest

from invitation_triage.calendar import MockCalendar, get_calendar_events
from invitation_triage.exceptions import CalendarError
from invitation_triage.models import CalendarEvent

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def calendar():
    """Provide a MockCalendar instance."""
    return MockCalendar()


@pytest.fixture
def cycle_start():
    """The base date for the two-week cycle."""
    return datetime(2026, 2, 2)


@pytest.fixture
def original_period():
    """Date range for the original template period (Feb 2-13, 2026)."""
    return (datetime(2026, 2, 2), datetime(2026, 2, 13, 23, 59, 59))


@pytest.fixture
def next_cycle_period():
    """Date range for the next cycle (Feb 16-27, 2026)."""
    return (datetime(2026, 2, 16), datetime(2026, 2, 27, 23, 59, 59))


# ============================================================================
# Calendar Initialization Tests
# ============================================================================


def test_calendar_initializes_correctly(calendar):
    """Calendar should initialize with template and constants."""
    assert calendar is not None
    assert calendar._template is not None
    assert calendar.CYCLE_START == datetime(2026, 2, 2)
    assert calendar.CYCLE_LENGTH_DAYS == 14


def test_template_has_14_days(calendar):
    """Template should contain exactly 14 cycle days (0-13)."""
    template = calendar._template
    assert len(template) == 14
    assert all(day in template for day in range(14))


def test_weekends_are_empty(calendar):
    """Weekends (days 5-6, 12-13) should have no events."""
    template = calendar._template
    assert len(template[5]) == 0, "Saturday week 1 should be empty"
    assert len(template[6]) == 0, "Sunday week 1 should be empty"
    assert len(template[12]) == 0, "Saturday week 2 should be empty"
    assert len(template[13]) == 0, "Sunday week 2 should be empty"


def test_weekdays_have_events(calendar):
    """All weekdays should have at least one event."""
    template = calendar._template
    weekdays = [0, 1, 2, 3, 4, 7, 8, 9, 10, 11]  # Mon-Fri for both weeks

    for day in weekdays:
        assert len(template[day]) > 0, f"Weekday {day} should have events"


# ============================================================================
# Template Content Tests
# ============================================================================


def test_mondays_have_po_briefing(calendar):
    """Both Mondays should start with PO morning briefing."""
    template = calendar._template

    # Monday week 1 (day 0)
    monday1_events = template[0]
    assert any("PO morning briefing" in event["title"] for event in monday1_events)
    assert monday1_events[0]["start_time"] == "2026-02-02 08:30"

    # Monday week 2 (day 7)
    monday2_events = template[7]
    assert any("PO morning briefing" in event["title"] for event in monday2_events)
    assert monday2_events[0]["start_time"] == "2026-02-09 08:30"


def test_all_events_have_required_fields(calendar):
    """Every template event should have all required fields."""
    template = calendar._template
    required_fields = [
        "title",
        "start_time",
        "end_time",
        "description",
        "priority",
        "location",
    ]

    for day, events in template.items():
        for event in events:
            for field in required_fields:
                assert field in event, f"Day {day} event missing {field}"


def test_event_priorities_are_valid(calendar):
    """All event priorities should be high, medium, or low."""
    template = calendar._template
    valid_priorities = {"high", "medium", "low"}

    for day, events in template.items():
        for event in events:
            assert event["priority"] in valid_priorities, (
                f"Invalid priority: {event['priority']}"
            )


def test_events_have_locations(calendar):
    """All events should have location specified."""
    template = calendar._template

    for day, events in template.items():
        for event in events:
            assert event["location"] is not None
            assert len(event["location"]) > 0


# ============================================================================
# Single Day Query Tests
# ============================================================================


def test_get_events_for_single_monday(calendar, cycle_start):
    """Getting events for a single Monday returns correct events."""
    events = calendar.get_events(cycle_start, cycle_start)

    assert len(events) == 6
    assert events[0].title == "PO morning briefing — day plan and priorities"
    assert events[0].start_time == datetime(2026, 2, 2, 8, 30)
    assert all(event.start_time.date() == cycle_start.date() for event in events)


def test_get_events_for_single_tuesday(calendar):
    """Getting events for a single Tuesday returns correct events."""
    tuesday = datetime(2026, 2, 3)
    events = calendar.get_events(tuesday, tuesday)

    assert len(events) == 6
    assert all(event.start_time.date() == tuesday.date() for event in events)


def test_get_events_for_weekend_returns_empty(calendar):
    """Weekend days should return no events."""
    saturday = datetime(2026, 2, 7)
    sunday = datetime(2026, 2, 8)

    saturday_events = calendar.get_events(saturday, saturday)
    sunday_events = calendar.get_events(sunday, sunday)

    assert len(saturday_events) == 0
    assert len(sunday_events) == 0


def test_event_times_match_requested_date(calendar):
    """Events should have times from template but date from request."""
    # Query a Monday far in the future
    future_monday = datetime(2027, 6, 7)  # Random Monday in 2027
    events = calendar.get_events(future_monday, future_monday)

    # Should have Monday's events
    assert len(events) > 0

    # All events should be on the requested date
    assert all(event.start_time.date() == future_monday.date() for event in events)

    # First event should still be at 08:30 (template time)
    assert events[0].start_time.hour == 8
    assert events[0].start_time.minute == 30


# ============================================================================
# Date Range Query Tests
# ============================================================================


def test_get_events_for_full_week(calendar):
    """Getting events for a full week returns all weekday events."""
    start = datetime(2026, 2, 2)  # Monday
    end = datetime(2026, 2, 8, 23, 59, 59)  # Sunday

    events = calendar.get_events(start, end)

    # Should have events for Mon-Fri (days 0-4), none for Sat-Sun
    assert len(events) > 0
    # Count should be sum of weekday events only
    assert len(events) == 6 + 6 + 6 + 3 + 6  # Mon + Tue + Wed + Thu + Fri


def test_get_events_for_two_weeks(calendar, original_period):
    """Getting events for full two-week period returns all events."""
    start, end = original_period
    events = calendar.get_events(start, end)

    # 10 weekdays worth of events
    assert len(events) == 55  # Total events in the template


def test_get_events_spans_weekend(calendar):
    """Date range spanning weekend should skip weekend days."""
    start = datetime(2026, 2, 6)  # Friday
    end = datetime(2026, 2, 10, 23, 59, 59)  # Tuesday

    events = calendar.get_events(start, end)

    # Should have Fri + Mon + Tue events, no Sat/Sun
    # All events should be on weekdays
    event_dates = {event.start_time.date() for event in events}
    assert datetime(2026, 2, 7).date() not in event_dates  # Saturday
    assert datetime(2026, 2, 8).date() not in event_dates  # Sunday


# ============================================================================
# Cycle Repetition Tests
# ============================================================================


def test_cycle_repeats_after_14_days(calendar, original_period, next_cycle_period):
    """Events should repeat exactly after 14 days."""
    orig_start, orig_end = original_period
    next_start, next_end = next_cycle_period

    orig_events = calendar.get_events(orig_start, orig_end)
    next_events = calendar.get_events(next_start, next_end)

    # Same number of events
    assert len(orig_events) == len(next_events)

    # Same titles in same order
    orig_titles = [e.title for e in orig_events]
    next_titles = [e.title for e in next_events]
    assert orig_titles == next_titles


def test_monday_repeats_every_14_days(calendar, cycle_start):
    """Mondays should have identical events every 14 days."""
    mondays = [
        cycle_start,
        cycle_start + timedelta(days=14),
        cycle_start + timedelta(days=28),
        cycle_start + timedelta(days=42),
    ]

    events_per_monday = [calendar.get_events(m, m) for m in mondays]

    # All Mondays should have same number of events
    event_counts = [len(events) for events in events_per_monday]
    assert len(set(event_counts)) == 1, "All Mondays should have same event count"

    # All Mondays should have same event titles
    titles = [[e.title for e in events] for events in events_per_monday]
    assert all(t == titles[0] for t in titles), "All Mondays should have same titles"


def test_cycle_works_far_in_future(calendar):
    """Calendar should work correctly years in the future."""
    # June 2, 2027 (over a year later)
    future_date = datetime(2027, 6, 2)
    events = calendar.get_events(future_date, future_date)

    # Should still have events
    assert len(events) > 0

    # Should match the correct cycle day
    days_since_start = (future_date - calendar.CYCLE_START).days
    cycle_day = days_since_start % 14

    expected_event_count = len(calendar._template[cycle_day])
    assert len(events) == expected_event_count


def test_cycle_works_in_past(calendar, cycle_start):
    """Calendar should work for dates before cycle start (negative modulo)."""
    # 14 days before cycle start
    past_date = cycle_start - timedelta(days=14)
    events = calendar.get_events(past_date, past_date)

    # Should have same events as cycle_start (both are cycle day 0)
    current_events = calendar.get_events(cycle_start, cycle_start)

    assert len(events) == len(current_events)
    assert [e.title for e in events] == [e.title for e in current_events]


# ============================================================================
# CalendarEvent Object Tests
# ============================================================================


def test_returns_calendar_event_objects(calendar, cycle_start):
    """get_events should return CalendarEvent instances."""
    events = calendar.get_events(cycle_start, cycle_start)

    assert all(isinstance(event, CalendarEvent) for event in events)


def test_calendar_events_have_all_fields(calendar, cycle_start):
    """CalendarEvent objects should have all expected fields."""
    events = calendar.get_events(cycle_start, cycle_start)

    for event in events:
        assert hasattr(event, "title")
        assert hasattr(event, "start_time")
        assert hasattr(event, "end_time")
        assert hasattr(event, "description")
        assert hasattr(event, "priority")
        assert hasattr(event, "location")


def test_event_times_are_datetime_objects(calendar, cycle_start):
    """Event start_time and end_time should be datetime objects."""
    events = calendar.get_events(cycle_start, cycle_start)

    for event in events:
        assert isinstance(event.start_time, datetime)
        assert isinstance(event.end_time, datetime)


def test_event_end_time_after_start_time(calendar, cycle_start):
    """All events should have end_time after start_time."""
    events = calendar.get_events(cycle_start, cycle_start)

    for event in events:
        assert event.end_time > event.start_time, (
            f"Event {event.title} has invalid time range"
        )


def test_events_are_chronologically_ordered(calendar, cycle_start):
    """Events within a day should be in chronological order."""
    events = calendar.get_events(cycle_start, cycle_start)

    for i in range(len(events) - 1):
        assert events[i].start_time <= events[i + 1].start_time, (
            "Events should be chronologically ordered"
        )


# ============================================================================
# Edge Cases and Boundary Tests
# ============================================================================


def test_same_start_and_end_date(calendar):
    """Start and end being the same date should work."""
    date = datetime(2026, 2, 5)
    events = calendar.get_events(date, date)

    assert len(events) > 0
    assert all(event.start_time.date() == date.date() for event in events)


def test_end_date_before_midnight(calendar):
    """End date without time should still include full day."""
    start = datetime(2026, 2, 2)
    end = datetime(2026, 2, 2, 23, 59, 59)

    events = calendar.get_events(start, end)
    assert len(events) == 6  # Full Monday


def test_query_spanning_multiple_cycles(calendar):
    """Query spanning multiple 14-day cycles should work."""
    start = datetime(2026, 2, 2)
    end = datetime(2026, 3, 15, 23, 59, 59)  # ~6 weeks

    events = calendar.get_events(start, end)

    # Should have events for multiple cycles
    assert len(events) > 55  # More than one cycle worth


def test_query_single_hour_window(calendar):
    """Query with start and end on same day should work."""
    start = datetime(2026, 2, 2, 9, 0)
    end = datetime(2026, 2, 2, 10, 0)

    events = calendar.get_events(start, end)

    # Should still get all events for that day
    assert len(events) > 0


# ============================================================================
# Integration Tests with get_calendar_events Function
# ============================================================================


def test_get_calendar_events_uses_mock_by_default():
    """get_calendar_events should use MockCalendar by default."""
    start = datetime(2026, 2, 2)
    end = datetime(2026, 2, 2)

    events = get_calendar_events(start, end)

    assert len(events) > 0
    assert isinstance(events[0], CalendarEvent)


def test_get_calendar_events_accepts_custom_provider(calendar):
    """get_calendar_events should accept a custom provider."""
    start = datetime(2026, 2, 2)
    end = datetime(2026, 2, 2)

    events = get_calendar_events(start, end, provider=calendar)

    assert len(events) > 0


def test_get_calendar_events_validates_date_range():
    """get_calendar_events should raise error for invalid range."""
    start = datetime(2026, 2, 10)
    end = datetime(2026, 2, 2)  # End before start

    with pytest.raises(CalendarError, match="Invalid date range"):
        get_calendar_events(start, end)


def test_get_calendar_events_wraps_provider_errors(calendar):
    """get_calendar_events should wrap provider exceptions."""

    # Create a broken provider
    class BrokenProvider:
        def get_events(self, start, end):
            raise RuntimeError("Provider failed")

    start = datetime(2026, 2, 2)
    end = datetime(2026, 2, 2)

    with pytest.raises(CalendarError, match="Calendar provider failed"):
        get_calendar_events(start, end, provider=BrokenProvider())


# ============================================================================
# Realistic Scenario Tests
# ============================================================================


def test_check_availability_for_invitation(calendar):
    """Simulate checking if minister is available for an invitation."""
    # Invitation on Monday Feb 2 at 14:00-15:00
    invitation_date = datetime(2026, 2, 2)
    invitation_start = datetime(2026, 2, 2, 14, 0)
    invitation_end = datetime(2026, 2, 2, 15, 0)

    events = calendar.get_events(invitation_date, invitation_date)

    # Check if any events conflict
    conflicts = [
        event
        for event in events
        if (event.start_time < invitation_end and event.end_time > invitation_start)
    ]

    # There should be a conflict (ARIA meeting at 15:15 is close but no overlap)
    # No events between 13:00-15:15 on this day
    assert len(conflicts) == 0, "14:00-15:00 should be free"


def test_get_week_overview(calendar):
    """Simulate getting a week overview for planning."""
    start = datetime(2026, 2, 2)
    end = datetime(2026, 2, 8, 23, 59, 59)

    events = calendar.get_events(start, end)

    # Group by day
    events_by_day = {}
    for event in events:
        day = event.start_time.date()
        if day not in events_by_day:
            events_by_day[day] = []
        events_by_day[day].append(event)

    # Should have 5 weekdays
    assert len(events_by_day) == 5

    # Each day should have multiple events
    for day, day_events in events_by_day.items():
        assert len(day_events) > 0


def test_find_next_available_monday_morning(calendar, cycle_start):
    """Find the next Monday morning slot available."""
    # Monday mornings start with PO briefing at 08:30-09:00
    # Next available is 09:15

    events = calendar.get_events(cycle_start, cycle_start)
    morning_events = [e for e in events if e.start_time.hour < 12]

    # First event at 08:30
    assert morning_events[0].start_time.hour == 8
    assert morning_events[0].start_time.minute == 30

    # Gap after first event before next at 09:15
    assert morning_events[1].start_time.hour == 9
    assert morning_events[1].start_time.minute == 15


# ============================================================================
# Performance and Stress Tests
# ============================================================================


def test_large_date_range_performance(calendar):
    """Calendar should handle large date ranges efficiently."""
    start = datetime(2026, 1, 1)
    end = datetime(2027, 12, 31)  # 2 full years

    events = calendar.get_events(start, end)

    # Should complete without hanging
    assert len(events) > 1000  # Many cycles worth


def test_many_single_day_queries(calendar):
    """Multiple single-day queries should be fast."""
    dates = [datetime(2026, 2, 2) + timedelta(days=i) for i in range(100)]

    for date in dates:
        events = calendar.get_events(date, date)
        assert isinstance(events, list)


# ============================================================================
# Documentation and Metadata Tests
# ============================================================================


def test_calendar_has_docstring(calendar):
    """MockCalendar should have documentation."""
    assert MockCalendar.__doc__ is not None
    assert "two-week" in MockCalendar.__doc__.lower()
    assert "groundhog" in MockCalendar.__doc__.lower()


def test_cycle_constants_documented(calendar):
    """Cycle constants should be accessible and documented."""
    assert hasattr(calendar, "CYCLE_START")
    assert hasattr(calendar, "CYCLE_LENGTH_DAYS")
    assert calendar.CYCLE_LENGTH_DAYS == 14
