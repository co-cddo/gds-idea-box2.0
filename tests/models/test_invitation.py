# tests/test_invitation.py

"""
Tests for invitation models.
"""

from invitation_triage.models import EventType, Invitation, NotInvitation

# ============================================================================
# EventType Tests
# ============================================================================


def test_event_type_enum_values():
    """Test that EventType enum has expected values."""
    assert EventType.MEETING == "meeting"
    assert EventType.SPEECH == "speech"
    assert EventType.PANEL == "panel"
    assert EventType.RECEPTION == "reception"
    assert EventType.SITE_VISIT == "site_visit"
    assert EventType.CONFERENCE == "conference"
    assert EventType.OTHER == "other"


# ============================================================================
# NotInvitation Tests
# ============================================================================


def test_not_invitation_creation():
    """Test creating a NotInvitation."""
    not_invite = NotInvitation(
        email_id="test123", reason="This is just an informational update"
    )

    assert not_invite.email_id == "test123"
    assert "informational" in not_invite.reason


def test_not_invitation_from_dict():
    """Test creating NotInvitation from dict (JSON)."""
    data = {"email_id": "abc123", "reason": "Thank you note, not an invitation"}

    not_invite = NotInvitation(**data)
    assert not_invite.email_id == "abc123"


# ============================================================================
# Invitation Tests
# ============================================================================


def test_invitation_creation_all_fields():
    """Test creating an Invitation with all fields."""
    invite = Invitation(
        email_id="test123",
        event_type=EventType.RECEPTION,
        host_org="The Royal Society",
        purpose="AI safety research launch",
        event_summary="Reception celebrating new AI safety research findings.",
        topics=["ai_and_digital", "science_research_ecosystem"],
        proposed_times=["15th February 2026, 6:00 PM"],
        is_time_flexible=False,
        location="The Royal Society, London",
        deadline_to_respond="5th February 2026",
        overall_confidence=0.95,
    )

    assert invite.email_id == "test123"
    assert invite.event_type == EventType.RECEPTION
    assert invite.host_org == "The Royal Society"
    assert len(invite.topics) == 2
    assert invite.is_time_flexible is False


def test_invitation_optional_fields():
    """Test that optional fields can be omitted."""
    invite = Invitation(
        email_id="test123",
        event_type=EventType.MEETING,
        host_org="DSIT",
        purpose="Budget discussion",
        event_summary="Quarterly budget review meeting.",
        topics=["research_and_development"],
        proposed_times=["Next Tuesday"],
        is_time_flexible=True,
        location="Westminster",
    )

    assert invite.deadline_to_respond is None
    assert invite.overall_confidence is None


def test_invitation_multiple_proposed_times():
    """Test invitation with multiple time options."""
    invite = Invitation(
        email_id="test123",
        event_type=EventType.PANEL,
        host_org="Cambridge University",
        purpose="Quantum tech panel",
        event_summary="Panel discussion on quantum commercialization.",
        topics=["quantum_technologies"],
        proposed_times=["Tuesday 10th March, 2:00 PM", "Wednesday 11th March, 9:30 AM"],
        is_time_flexible=True,
        location="Churchill College, Cambridge",
    )

    assert len(invite.proposed_times) == 2
    assert invite.is_time_flexible is True


def test_invitation_confidence_validation():
    """Test that confidence score is validated (0.0 to 1.0)."""
    import pytest
    from pydantic import ValidationError

    # Valid confidence
    invite = Invitation(
        email_id="test",
        event_type=EventType.OTHER,
        host_org="Test Org",
        purpose="Test",
        event_summary="Test summary",
        topics=[],
        proposed_times=["Soon"],
        is_time_flexible=False,
        location="Somewhere",
        overall_confidence=0.5,
    )
    assert invite.overall_confidence == 0.5

    # Invalid confidence (too high)
    with pytest.raises(ValidationError):
        Invitation(
            email_id="test",
            event_type=EventType.OTHER,
            host_org="Test Org",
            purpose="Test",
            event_summary="Test summary",
            topics=[],
            proposed_times=["Soon"],
            is_time_flexible=False,
            location="Somewhere",
            overall_confidence=1.5,  # Invalid: > 1.0
        )


def test_invitation_from_dict():
    """Test creating Invitation from dict (simulating JSON parsing)."""
    data = {
        "email_id": "abc123",
        "event_type": "speech",
        "host_org": "Tech Conference 2026",
        "purpose": "Keynote on AI policy",
        "event_summary": "Opening keynote address on UK AI strategy.",
        "topics": ["ai_and_digital", "tech_innovation"],
        "proposed_times": ["March 15, 2026, 9:00 AM"],
        "is_time_flexible": False,
        "location": "ExCeL London",
    }

    invite = Invitation(**data)
    assert invite.event_type == EventType.SPEECH
    assert len(invite.topics) == 2


def test_invitation_empty_topics_list():
    """Test that topics can be an empty list."""
    invite = Invitation(
        email_id="test",
        event_type=EventType.OTHER,
        host_org="Unknown",
        purpose="General meeting",
        event_summary="General purpose meeting.",
        topics=[],  # No clear topics
        proposed_times=["TBD"],
        is_time_flexible=True,
        location="TBD",
    )

    assert invite.topics == []
