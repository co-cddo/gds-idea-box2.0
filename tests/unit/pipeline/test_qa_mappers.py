"""Tests for QA stage mapper functions."""

import pytest

from box2.pipeline.mappers import (
    _split_list_field,
    to_sharepoint_fields,
    to_sharepoint_invitation_from_qa,
    to_sharepoint_invitation_qa,
)
from box2.pipeline.models import TriagedInvitation
from box2.triage.models import Invitation, SharepointInvitation, SharepointInvitationQA, TriagedDecision
from box2.triage.models.invitation import EventType

# ===== Fixtures =====


@pytest.fixture
def sample_invitation() -> Invitation:
    """Minimal valid Invitation for testing."""
    return Invitation(
        title="AI Safety Summit",
        document_id="doc-001",
        event_type=EventType.CONFERENCE,
        host_org="Royal Society",
        purpose="Discuss AI safety policy and international cooperation",
        event_summary="Annual conference on AI safety bringing together policymakers and researchers.",
        topics=["AI Safety", "International Collaboration"],
        proposed_times=["15th March 2026, 10:00 AM"],
        is_time_flexible=False,
        location="The Royal Society, London",
        deadline_to_respond="1st March 2026",
        urgency="not_urgent",
    )


@pytest.fixture
def sample_decision() -> TriagedDecision:
    """Minimal valid TriagedDecision for testing."""
    return TriagedDecision(
        title="AI Safety Summit",
        document_id="doc-001",
        decision="accept",
        priority="high",
        reason="Directly aligned with minister's AI safety priorities and portfolio responsibilities.",
        draft_response="Thank you for the invitation to the AI Safety Summit. The Minister is pleased to accept.",
        affected_events=["Cabinet Committee on AI"],
    )


@pytest.fixture
def sample_triaged(sample_invitation: Invitation, sample_decision: TriagedDecision) -> TriagedInvitation:
    """TriagedInvitation combining the sample invitation and decision."""
    return TriagedInvitation(invitation=sample_invitation, decision=sample_decision)


@pytest.fixture
def sample_qa_item_fields() -> dict:
    """Flat dict simulating a QA SharePoint list item's fields after reviewer edits."""
    return {
        "Title": "conference: Royal Society",
        "document_id": "doc-001",
        "event_type": "conference",
        "host_organisation": "Royal Society",
        "purpose": "Discuss AI safety policy and international cooperation",
        "event_summary": "Annual conference on AI safety bringing together policymakers and researchers.",
        "topics": "AI Safety; International Collaboration",
        "proposed_times": "15th March 2026, 10:00 AM",
        "is_time_flexible": False,
        "location": "The Royal Society, London",
        "deadline_to_respond": "1st March 2026",
        "model_decision": "accept",
        "priority": "high",
        "reason": "Directly aligned with minister's AI safety priorities.",
        "draft_response": "Thank you for the invitation. The Minister is pleased to accept.",
        "affected_events": "Cabinet Committee on AI",
        "urgency": "not_urgent",
        "qa_status": "approved",
        "qa_reviewer": "jane.smith@example.gov.uk",
        "qa_notes": "Looks correct, approved.",
    }


# ===== to_sharepoint_invitation_qa =====


def test_to_sharepoint_invitation_qa_returns_qa_model(sample_triaged: TriagedInvitation):
    """to_sharepoint_invitation_qa should return a SharepointInvitationQA instance."""
    result = to_sharepoint_invitation_qa(sample_triaged)
    assert isinstance(result, SharepointInvitationQA)


def test_to_sharepoint_invitation_qa_defaults_to_pending(sample_triaged: TriagedInvitation):
    """New QA items should have qa_status set to 'pending'."""
    result = to_sharepoint_invitation_qa(sample_triaged)
    assert result.qa_status == "pending"


def test_to_sharepoint_invitation_qa_qa_fields_default_to_none(sample_triaged: TriagedInvitation):
    """qa_reviewer and qa_notes should default to None for new items."""
    result = to_sharepoint_invitation_qa(sample_triaged)
    assert result.qa_reviewer is None
    assert result.qa_notes is None


def test_to_sharepoint_invitation_qa_preserves_invitation_fields(sample_triaged: TriagedInvitation):
    """All invitation and decision fields should be correctly mapped."""
    result = to_sharepoint_invitation_qa(sample_triaged)
    inv = sample_triaged.invitation
    dec = sample_triaged.decision

    assert result.title == f"{inv.event_type.value}: {inv.host_org}"
    assert result.document_id == inv.document_id
    assert result.event_type == inv.event_type.value
    assert result.host_organisation == inv.host_org
    assert result.purpose == inv.purpose
    assert result.topics == inv.topics
    assert result.proposed_times == inv.proposed_times
    assert result.is_time_flexible == inv.is_time_flexible
    assert result.location == inv.location
    assert result.deadline_to_respond == inv.deadline_to_respond
    assert result.model_decision == dec.decision
    assert result.priority == dec.priority
    assert result.reason == dec.reason
    assert result.draft_response == dec.draft_response
    assert result.affected_events == dec.affected_events
    assert result.urgency == inv.urgency


def test_to_sharepoint_invitation_qa_serialises_with_qa_fields(sample_triaged: TriagedInvitation):
    """to_sharepoint_fields should include qa_status in the serialised output."""
    qa_model = to_sharepoint_invitation_qa(sample_triaged)
    fields = to_sharepoint_fields(qa_model)

    assert fields["qa_status"] == "pending"
    assert "qa_reviewer" not in fields  # None values omitted
    assert "qa_notes" not in fields


# ===== to_sharepoint_invitation_from_qa =====


def test_to_sharepoint_invitation_from_qa_returns_base_model(sample_qa_item_fields: dict):
    """to_sharepoint_invitation_from_qa should return a SharepointInvitation (not QA variant)."""
    result = to_sharepoint_invitation_from_qa(sample_qa_item_fields)
    assert type(result) is SharepointInvitation


def test_to_sharepoint_invitation_from_qa_maps_scalar_fields(sample_qa_item_fields: dict):
    """Scalar fields should be correctly mapped from the QA item."""
    result = to_sharepoint_invitation_from_qa(sample_qa_item_fields)

    assert result.title == "conference: Royal Society"
    assert result.document_id == "doc-001"
    assert result.event_type == "conference"
    assert result.host_organisation == "Royal Society"
    assert result.purpose == "Discuss AI safety policy and international cooperation"
    assert result.is_time_flexible is False
    assert result.location == "The Royal Society, London"
    assert result.model_decision == "accept"
    assert result.priority == "high"
    assert result.urgency == "not_urgent"


def test_to_sharepoint_invitation_from_qa_splits_list_fields(sample_qa_item_fields: dict):
    """Semicolon-delimited list fields should be split back into Python lists."""
    result = to_sharepoint_invitation_from_qa(sample_qa_item_fields)

    assert result.topics == ["AI Safety", "International Collaboration"]
    assert result.proposed_times == ["15th March 2026, 10:00 AM"]
    assert result.affected_events == ["Cabinet Committee on AI"]


def test_to_sharepoint_invitation_from_qa_strips_qa_fields(sample_qa_item_fields: dict):
    """QA-specific fields should not appear on the resulting SharepointInvitation."""
    result = to_sharepoint_invitation_from_qa(sample_qa_item_fields)

    assert not hasattr(result, "qa_status")
    assert not hasattr(result, "qa_reviewer")
    assert not hasattr(result, "qa_notes")


def test_to_sharepoint_invitation_from_qa_handles_missing_optional_fields():
    """Missing optional fields should fall back to safe defaults."""
    minimal_fields = {
        "Title": "Test invite",
        "document_id": "doc-002",
        "event_summary": "A test event for validation purposes.",
        "purpose": "Testing the mapper with minimal fields",
        "host_organisation": "Test Org",
        "proposed_times": "1st Jan 2026",
        "reason": "Test reason text",
        "draft_response": "Test draft response text",
    }
    result = to_sharepoint_invitation_from_qa(minimal_fields)

    assert result.title == "Test invite"
    assert result.deadline_to_respond is None
    assert result.affected_events == []
    assert result.topics == []


# ===== _split_list_field =====


def test_split_list_field_splits_semicolon_string():
    """Semicolon-delimited strings should be split into a list."""
    assert _split_list_field("alpha; beta; gamma") == ["alpha", "beta", "gamma"]


def test_split_list_field_passes_through_list():
    """Already-split lists should be returned as-is."""
    assert _split_list_field(["a", "b"]) == ["a", "b"]


def test_split_list_field_returns_empty_for_none():
    """None input should return an empty list."""
    assert _split_list_field(None) == []


def test_split_list_field_returns_empty_for_empty_string():
    """Empty string input should return an empty list."""
    assert _split_list_field("") == []


def test_split_list_field_strips_whitespace():
    """Whitespace around semicolons should be stripped."""
    assert _split_list_field("  a ;  b  ; c  ") == ["a", "b", "c"]


def test_split_list_field_ignores_empty_segments():
    """Empty segments from trailing semicolons should be filtered out."""
    assert _split_list_field("a; ; b;") == ["a", "b"]
