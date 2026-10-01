"""Unit tests for the list review handler (minister decisions and comments -> actions)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from box2.pipeline.models import ActionReviewResult
from box2.receiver.route_handlers import make_list_review_handler

# ============================================================================
# make_list_review_handler (invitation) Tests
# ============================================================================


def _make_invitation_item(
    item_id: str = "1",
    minister_decision: str | None = "accept",
    minister_comment: str | None = None,
) -> dict:
    """Build a canned invitation list item."""
    return {
        "id": item_id,
        "fields": {
            "document_id": "doc-001",
            "minister_decision": minister_decision,
            "minister_comment": minister_comment,
        },
    }


@pytest.mark.anyio
async def test_handle_review_invitation_skips_when_no_minister_decision():
    """handle_review should skip an invitation item with no minister_decision."""
    actions_list = MagicMock()
    handler = make_list_review_handler(actions_list=actions_list, document_type="invitation")
    item = _make_invitation_item(minister_decision=None)

    with patch("box2.receiver.route_handlers.extract_actions_from_review") as mock_extract:
        await handler(item)

    mock_extract.assert_not_called()
    actions_list.create_item.assert_not_called()


@pytest.mark.anyio
async def test_handle_review_invitation_skips_when_other_decision_and_no_comment():
    """handle_review should skip when minister_decision is 'other' but no comment is provided."""
    actions_list = MagicMock()
    handler = make_list_review_handler(actions_list=actions_list, document_type="invitation")
    item = _make_invitation_item(minister_decision="other", minister_comment=None)

    with patch("box2.receiver.route_handlers.extract_actions_from_review") as mock_extract:
        await handler(item)

    mock_extract.assert_not_called()
    actions_list.create_item.assert_not_called()


@pytest.mark.anyio
async def test_handle_review_invitation_proceeds_when_other_decision_with_comment():
    """handle_review should proceed when minister_decision is 'other' and a comment is provided."""
    actions_list = MagicMock()
    handler = make_list_review_handler(actions_list=actions_list, document_type="invitation")
    item = _make_invitation_item(minister_decision="other", minister_comment="Please draft a holding response.")

    mock_result = MagicMock(spec=ActionReviewResult)
    mock_result.actions = []
    mock_extract = AsyncMock(return_value=mock_result)

    with patch("box2.receiver.route_handlers.extract_actions_from_review", new=mock_extract):
        await handler(item)

    mock_extract.assert_called_once()


@pytest.mark.anyio
async def test_handle_review_invitation_proceeds_when_accept_with_no_comment():
    """handle_review should proceed when minister_decision is 'accept' even without a comment."""
    actions_list = MagicMock()
    handler = make_list_review_handler(actions_list=actions_list, document_type="invitation")
    item = _make_invitation_item(minister_decision="accept", minister_comment=None)

    mock_result = MagicMock(spec=ActionReviewResult)
    mock_result.actions = []
    mock_extract = AsyncMock(return_value=mock_result)

    with patch("box2.receiver.route_handlers.extract_actions_from_review", new=mock_extract):
        await handler(item)

    mock_extract.assert_called_once()


@pytest.mark.anyio
async def test_handle_review_invitation_proceeds_when_decline_with_no_comment():
    """handle_review should proceed when minister_decision is 'decline' even without a comment."""
    actions_list = MagicMock()
    handler = make_list_review_handler(actions_list=actions_list, document_type="invitation")
    item = _make_invitation_item(minister_decision="decline", minister_comment=None)

    mock_result = MagicMock(spec=ActionReviewResult)
    mock_result.actions = []
    mock_extract = AsyncMock(return_value=mock_result)

    with patch("box2.receiver.route_handlers.extract_actions_from_review", new=mock_extract):
        await handler(item)

    mock_extract.assert_called_once()


@pytest.mark.anyio
async def test_handle_review_invitation_writes_one_item_per_action():
    """handle_review should call actions_list.create_item once per action returned."""
    actions_list = MagicMock()
    handler = make_list_review_handler(actions_list=actions_list, document_type="invitation")
    item = _make_invitation_item(minister_decision="accept")

    mock_result = MagicMock(spec=ActionReviewResult)
    mock_result.actions = [MagicMock(), MagicMock()]

    with (
        patch("box2.receiver.route_handlers.extract_actions_from_review", new=AsyncMock(return_value=mock_result)),
        patch("box2.receiver.route_handlers.to_sharepoint_action", return_value=MagicMock()),
        patch("box2.receiver.route_handlers.to_sharepoint_fields", return_value={}),
    ):
        await handler(item)

    assert actions_list.create_item.call_count == 2


@pytest.mark.anyio
async def test_handle_review_invitation_raises_on_extraction_failure():
    """handle_review should propagate exceptions from extract_actions_from_review."""
    actions_list = MagicMock()
    handler = make_list_review_handler(actions_list=actions_list, document_type="invitation")
    item = _make_invitation_item(minister_decision="accept")

    with (
        patch(
            "box2.receiver.route_handlers.extract_actions_from_review",
            new=AsyncMock(side_effect=RuntimeError("LLM failed")),
        ),
        pytest.raises(RuntimeError, match="LLM failed"),
    ):
        await handler(item)
