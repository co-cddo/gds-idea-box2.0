"""Tests for QA stage mapper functions and from_sharepoint_fields."""

import pytest
from pydantic import AnyHttpUrl, BaseModel, Field

from box2.pipeline.mappers import (
    _extract_urls_from_html,
    _split_list_field,
    from_sharepoint_fields,
    to_sharepoint_fields,
    to_sharepoint_invitation,
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


# ===== to_sharepoint_invitation (QA model → minister model) =====


def test_to_sharepoint_invitation_returns_base_model(sample_qa_item_fields: dict):
    """to_sharepoint_invitation should return a SharepointInvitation (not QA variant)."""
    qa_item = from_sharepoint_fields(sample_qa_item_fields, SharepointInvitationQA)
    result = to_sharepoint_invitation(qa_item)
    assert type(result) is SharepointInvitation


def test_to_sharepoint_invitation_maps_fields(sample_qa_item_fields: dict):
    """Fields should be correctly mapped from the QA model to the invitation model."""
    qa_item = from_sharepoint_fields(sample_qa_item_fields, SharepointInvitationQA)
    result = to_sharepoint_invitation(qa_item)

    assert result.title == "conference: Royal Society"
    assert result.document_id == "doc-001"
    assert result.host_organisation == "Royal Society"
    assert result.topics == ["AI Safety", "International Collaboration"]
    assert result.proposed_times == ["15th March 2026, 10:00 AM"]
    assert result.affected_events == ["Cabinet Committee on AI"]
    assert result.model_decision == "accept"
    assert result.priority == "high"


def test_to_sharepoint_invitation_strips_qa_fields(sample_qa_item_fields: dict):
    """QA-specific fields should not appear on the resulting SharepointInvitation."""
    qa_item = from_sharepoint_fields(sample_qa_item_fields, SharepointInvitationQA)
    result = to_sharepoint_invitation(qa_item)

    assert not hasattr(result, "qa_status")
    assert not hasattr(result, "qa_reviewer")
    assert not hasattr(result, "qa_notes")


# ===== from_sharepoint_fields =====


def test_from_sharepoint_fields_maps_title(sample_qa_item_fields: dict):
    """The SharePoint 'Title' key should be mapped to the model's 'title' field."""
    result = from_sharepoint_fields(sample_qa_item_fields, SharepointInvitationQA)
    assert result.title == "conference: Royal Society"


def test_from_sharepoint_fields_splits_list_fields(sample_qa_item_fields: dict):
    """Semicolon-delimited string fields should be split into Python lists."""
    result = from_sharepoint_fields(sample_qa_item_fields, SharepointInvitationQA)

    assert result.topics == ["AI Safety", "International Collaboration"]
    assert result.proposed_times == ["15th March 2026, 10:00 AM"]
    assert result.affected_events == ["Cabinet Committee on AI"]


def test_from_sharepoint_fields_preserves_scalar_fields(sample_qa_item_fields: dict):
    """Scalar fields should pass through unchanged."""
    result = from_sharepoint_fields(sample_qa_item_fields, SharepointInvitationQA)

    assert result.document_id == "doc-001"
    assert result.event_type == "conference"
    assert result.is_time_flexible is False
    assert result.model_decision == "accept"
    assert result.qa_status == "approved"
    assert result.qa_reviewer == "jane.smith@example.gov.uk"


def test_from_sharepoint_fields_ignores_extra_keys():
    """SharePoint system fields not on the model should be silently ignored."""
    fields = {
        "Title": "Test",
        "document_id": "doc-001",
        "event_type": "conference",
        "host_organisation": "Test Org",
        "purpose": "Testing with extra fields",
        "event_summary": "A test event for validation purposes.",
        "topics": "AI Safety",
        "proposed_times": "1st Jan 2026",
        "is_time_flexible": False,
        "location": "London",
        "model_decision": "accept",
        "priority": "high",
        "reason": "Test reason text here.",
        "draft_response": "Test draft response text.",
        "urgency": "not_urgent",
        # SharePoint system fields that aren't on the model:
        "Modified": "2026-01-01T00:00:00Z",
        "Created": "2026-01-01T00:00:00Z",
        "AuthorLookupId": "42",
    }
    result = from_sharepoint_fields(fields, SharepointInvitation)
    assert result.title == "Test"


def test_from_sharepoint_fields_handles_missing_optional_fields():
    """Missing optional fields should use model defaults."""
    fields = {
        "Title": "Test invite",
        "document_id": "doc-002",
        "event_type": "conference",
        "host_organisation": "Test Org",
        "purpose": "Testing the mapper with minimal fields",
        "event_summary": "A test event for validation purposes.",
        "topics": "",
        "proposed_times": "1st Jan 2026",
        "is_time_flexible": False,
        "location": "London",
        "model_decision": "accept",
        "priority": "high",
        "reason": "Test reason text here.",
        "draft_response": "Test draft response text.",
        "urgency": "not_urgent",
    }
    result = from_sharepoint_fields(fields, SharepointInvitation)

    assert result.deadline_to_respond is None
    assert result.affected_events == []
    assert result.topics == []


class _MockUrlModel(BaseModel):
    """Test model with a URL list field."""

    title: str = Field(description="Title")
    links: list[AnyHttpUrl] = Field(default_factory=list, description="URLs")


def test_from_sharepoint_fields_extracts_urls_from_html():
    """HTML anchor tags should be parsed back into URL lists."""
    fields = {
        "Title": "Test",
        "links": '<a href="https://www.gov.uk/example">https://www.gov.uk/example</a>'
        "<br>"
        '<a href="https://example.com/page">https://example.com/page</a>',
    }
    result = from_sharepoint_fields(fields, _MockUrlModel)

    assert [str(u) for u in result.links] == [
        "https://www.gov.uk/example",
        "https://example.com/page",
    ]


def test_from_sharepoint_fields_empty_url_html():
    """An empty HTML string should produce an empty URL list."""
    fields = {"Title": "Test", "links": ""}
    result = from_sharepoint_fields(fields, _MockUrlModel)
    assert result.links == []


def test_from_sharepoint_fields_round_trip(sample_triaged: TriagedInvitation):
    """Serialising then deserialising a model should produce equivalent data."""
    original = to_sharepoint_invitation_qa(sample_triaged)
    serialised = to_sharepoint_fields(original)
    restored = from_sharepoint_fields(serialised, SharepointInvitationQA)

    assert restored.title == original.title
    assert restored.document_id == original.document_id
    assert restored.topics == original.topics
    assert restored.proposed_times == original.proposed_times
    assert restored.affected_events == original.affected_events
    assert restored.qa_status == original.qa_status
    assert restored.model_decision == original.model_decision


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


# ===== _extract_urls_from_html =====


def test_extract_urls_from_html_single_link():
    """A single anchor tag should produce a one-element list."""
    html = '<a href="https://example.com">https://example.com</a>'
    assert _extract_urls_from_html(html) == ["https://example.com"]


def test_extract_urls_from_html_multiple_links():
    """Multiple anchor tags separated by <br> should all be extracted."""
    html = '<a href="https://a.com">a</a><br><a href="https://b.com">b</a>'
    assert _extract_urls_from_html(html) == ["https://a.com", "https://b.com"]


def test_extract_urls_from_html_empty_string():
    """An empty string should return an empty list."""
    assert _extract_urls_from_html("") == []
