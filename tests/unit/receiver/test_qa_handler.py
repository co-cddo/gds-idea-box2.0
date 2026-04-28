"""Unit tests for QA review handler and file upload handler QA routing."""

from unittest.mock import MagicMock

import pytest

from box2.receiver.route_handlers import make_qa_review_handler


# ============================================================================
# Fixtures
# ============================================================================


def _make_qa_item(
    item_id: str = "qa-1",
    qa_status: str = "pending",
    qa_reviewer: str | None = None,
    qa_notes: str | None = None,
) -> dict:
    """Build a canned QA list item response."""
    fields = {
        "Title": "conference: Royal Society",
        "document_id": "doc-001",
        "event_type": "conference",
        "host_organisation": "Royal Society",
        "purpose": "Discuss AI safety policy",
        "event_summary": "Annual conference on AI safety.",
        "topics": "AI Safety; International Collaboration",
        "proposed_times": "15th March 2026, 10:00 AM",
        "is_time_flexible": False,
        "location": "The Royal Society, London",
        "model_decision": "accept",
        "priority": "high",
        "reason": "Aligned with AI safety priorities.",
        "draft_response": "Thank you for the invitation. The Minister is pleased to accept.",
        "affected_events": "Cabinet Committee on AI",
        "urgency": "not_urgent",
        "qa_status": qa_status,
    }
    if qa_reviewer is not None:
        fields["qa_reviewer"] = qa_reviewer
    if qa_notes is not None:
        fields["qa_notes"] = qa_notes

    return {"id": item_id, "fields": fields}


@pytest.fixture()
def invitation_list() -> MagicMock:
    """Mock ListClient for the minister-facing invitations list."""
    mock = MagicMock()
    mock.list_name = "Invitations"
    return mock


@pytest.fixture()
def rejected_list() -> MagicMock:
    """Mock ListClient for the rejected invitations list."""
    mock = MagicMock()
    mock.list_name = "Rejected Invitations"
    return mock


@pytest.fixture()
def qa_list() -> MagicMock:
    """Mock ListClient for the QA invitations list."""
    mock = MagicMock()
    mock.list_name = "QA Invitations"
    return mock


# ============================================================================
# Approved flow
# ============================================================================


@pytest.mark.anyio
async def test_approved_item_written_to_invitation_list(invitation_list, rejected_list, qa_list):
    """An approved QA item should be copied to the minister's invitation list."""
    handler = make_qa_review_handler(invitation_list, rejected_list, qa_list)
    item = _make_qa_item(qa_status="approved")

    await handler(item)

    invitation_list.create_item.assert_called_once()
    fields = invitation_list.create_item.call_args[0][0]
    assert fields["Title"] == "conference: Royal Society"
    assert fields["document_id"] == "doc-001"


@pytest.mark.anyio
async def test_approved_item_deleted_from_qa_list(invitation_list, rejected_list, qa_list):
    """After approval, the item should be deleted from the QA list."""
    handler = make_qa_review_handler(invitation_list, rejected_list, qa_list)
    item = _make_qa_item(item_id="qa-42", qa_status="approved")

    await handler(item)

    qa_list.delete_item.assert_called_once_with("qa-42")


@pytest.mark.anyio
async def test_approved_item_not_written_to_rejected_list(invitation_list, rejected_list, qa_list):
    """An approved item should not appear in the rejected list."""
    handler = make_qa_review_handler(invitation_list, rejected_list, qa_list)
    item = _make_qa_item(qa_status="approved")

    await handler(item)

    rejected_list.create_item.assert_not_called()


@pytest.mark.anyio
async def test_approved_item_strips_qa_fields(invitation_list, rejected_list, qa_list):
    """QA-specific fields should not be present on the item written to the invitation list."""
    handler = make_qa_review_handler(invitation_list, rejected_list, qa_list)
    item = _make_qa_item(qa_status="approved", qa_reviewer="reviewer@gov.uk", qa_notes="Looks good")

    await handler(item)

    fields = invitation_list.create_item.call_args[0][0]
    assert "qa_status" not in fields
    assert "qa_reviewer" not in fields
    assert "qa_notes" not in fields


# ============================================================================
# Rejected flow
# ============================================================================


@pytest.mark.anyio
async def test_rejected_item_written_to_rejected_list(invitation_list, rejected_list, qa_list):
    """A rejected QA item should be copied to the rejected invitations list."""
    handler = make_qa_review_handler(invitation_list, rejected_list, qa_list)
    item = _make_qa_item(qa_status="rejected", qa_notes="Incorrect extraction")

    await handler(item)

    rejected_list.create_item.assert_called_once()
    fields = rejected_list.create_item.call_args[0][0]
    assert fields["qa_status"] == "rejected"
    assert fields["qa_notes"] == "Incorrect extraction"


@pytest.mark.anyio
async def test_rejected_item_deleted_from_qa_list(invitation_list, rejected_list, qa_list):
    """After rejection, the item should be deleted from the QA list."""
    handler = make_qa_review_handler(invitation_list, rejected_list, qa_list)
    item = _make_qa_item(item_id="qa-99", qa_status="rejected")

    await handler(item)

    qa_list.delete_item.assert_called_once_with("qa-99")


@pytest.mark.anyio
async def test_rejected_item_not_written_to_invitation_list(invitation_list, rejected_list, qa_list):
    """A rejected item should not appear in the minister's invitation list."""
    handler = make_qa_review_handler(invitation_list, rejected_list, qa_list)
    item = _make_qa_item(qa_status="rejected")

    await handler(item)

    invitation_list.create_item.assert_not_called()


@pytest.mark.anyio
async def test_rejected_item_preserves_qa_reviewer(invitation_list, rejected_list, qa_list):
    """The QA reviewer identity should be preserved in the rejected list for audit."""
    handler = make_qa_review_handler(invitation_list, rejected_list, qa_list)
    item = _make_qa_item(qa_status="rejected", qa_reviewer="jane@gov.uk", qa_notes="Wrong event type")

    await handler(item)

    fields = rejected_list.create_item.call_args[0][0]
    assert fields["qa_reviewer"] == "jane@gov.uk"
    assert fields["qa_notes"] == "Wrong event type"


# ============================================================================
# Pending / skip flow
# ============================================================================


@pytest.mark.anyio
async def test_pending_item_skipped(invitation_list, rejected_list, qa_list):
    """Items with qa_status='pending' should be skipped entirely."""
    handler = make_qa_review_handler(invitation_list, rejected_list, qa_list)
    item = _make_qa_item(qa_status="pending")

    await handler(item)

    invitation_list.create_item.assert_not_called()
    rejected_list.create_item.assert_not_called()
    qa_list.delete_item.assert_not_called()


@pytest.mark.anyio
async def test_missing_qa_status_defaults_to_skip(invitation_list, rejected_list, qa_list):
    """Items without a qa_status field should be treated as pending and skipped."""
    handler = make_qa_review_handler(invitation_list, rejected_list, qa_list)
    item = {"id": "qa-1", "fields": {"Title": "Test", "document_id": "doc-001"}}

    await handler(item)

    invitation_list.create_item.assert_not_called()
    rejected_list.create_item.assert_not_called()
    qa_list.delete_item.assert_not_called()


# ============================================================================
# Error handling
# ============================================================================


@pytest.mark.anyio
async def test_approved_item_not_deleted_if_create_fails(invitation_list, rejected_list, qa_list):
    """If writing to the invitation list fails, the QA item should not be deleted."""
    handler = make_qa_review_handler(invitation_list, rejected_list, qa_list)
    invitation_list.create_item.side_effect = RuntimeError("API error")
    item = _make_qa_item(qa_status="approved")

    with pytest.raises(RuntimeError, match="API error"):
        await handler(item)

    qa_list.delete_item.assert_not_called()


@pytest.mark.anyio
async def test_rejected_item_not_deleted_if_create_fails(invitation_list, rejected_list, qa_list):
    """If writing to the rejected list fails, the QA item should not be deleted."""
    handler = make_qa_review_handler(invitation_list, rejected_list, qa_list)
    rejected_list.create_item.side_effect = RuntimeError("API error")
    item = _make_qa_item(qa_status="rejected")

    with pytest.raises(RuntimeError, match="API error"):
        await handler(item)

    qa_list.delete_item.assert_not_called()
