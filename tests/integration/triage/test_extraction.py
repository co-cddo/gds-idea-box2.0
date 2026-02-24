"""
Integration tests for invitation extraction.

These are deterministic tests that verify the LLM produces structurally
valid output. They should pass consistently at temperature 0.3.

Results are cached per test case so each email is extracted once.
"""

import pytest

from box2.triage.invitation_extraction import extract_invitation
from box2.triage.models import Invitation, NotInvitation, SafeDocument
from box2.triage.models.document import generate_document_id
from box2.triage.models.invitation import EventType
from tests.unit.triage.test_emails_dataset import TEST_EMAILS

pytestmark = [pytest.mark.integration, pytest.mark.anyio]

# ============================================================================
# Helpers
# ============================================================================

_INVITATION_CASES = [tc for tc in TEST_EMAILS if tc["is_invitation"]]
_NOT_INVITATION_CASES = [tc for tc in TEST_EMAILS if not tc["is_invitation"]]


def create_safe_document_from_test(test_case: dict) -> SafeDocument:
    """Convert a test case dictionary to a SafeDocument object for extraction."""
    content = f"{test_case['subject']}\n{test_case['body']}"
    doc_id = generate_document_id(content, prefix="email")

    return SafeDocument(
        document_id=doc_id,
        filename=f"{test_case['email_id']}.eml",
        source_type="email",
        safe_text=content,
        document_timestamp=test_case["received_date"],
        pii_extracted={"emails": [], "phone_numbers": []},
        links_extracted=[],
    )


# Cache extraction results so each email is only extracted once.
# All test functions below evaluate different properties of the same output.
_extraction_cache: dict[str, Invitation | NotInvitation] = {}


async def _get_extraction_result(test_case: dict) -> Invitation | NotInvitation:
    """Return a cached extraction result, calling the LLM only on first access."""
    email_id = test_case["email_id"]
    if email_id not in _extraction_cache:
        safe_doc = create_safe_document_from_test(test_case)
        _extraction_cache[email_id] = await extract_invitation(safe_doc)
    return _extraction_cache[email_id]


# ============================================================================
# Classification Tests
# ============================================================================


@pytest.mark.parametrize("test_case", TEST_EMAILS, ids=lambda x: x["email_id"])
async def test_classification_accuracy(test_case):
    """Test that each email is correctly classified as invitation or not."""
    result = await _get_extraction_result(test_case)

    expected_is_invitation = test_case["is_invitation"]
    actual_is_invitation = isinstance(result, Invitation)

    assert expected_is_invitation == actual_is_invitation, (
        f"Classification failed for {test_case['email_id']}. "
        f"Expected: {expected_is_invitation}, Got: {actual_is_invitation}"
    )


# ============================================================================
# Document ID Passthrough
# ============================================================================


@pytest.mark.parametrize("test_case", TEST_EMAILS, ids=lambda x: x["email_id"])
async def test_document_id_passthrough(test_case):
    """Test that the system-assigned document_id is preserved through extraction."""
    safe_doc = create_safe_document_from_test(test_case)
    result = await _get_extraction_result(test_case)

    assert result.document_id == safe_doc.document_id, (
        f"document_id mismatch: expected {safe_doc.document_id}, got {result.document_id}"
    )


# ============================================================================
# Structural Tests -- Invitation Results
# ============================================================================


@pytest.mark.parametrize("test_case", _INVITATION_CASES, ids=lambda x: x["email_id"])
async def test_invitation_has_proposed_times(test_case):
    """Test that every invitation has at least one proposed time."""
    result = await _get_extraction_result(test_case)
    assert isinstance(result, Invitation)
    assert len(result.proposed_times) >= 1, "proposed_times must not be empty"


@pytest.mark.parametrize("test_case", _INVITATION_CASES, ids=lambda x: x["email_id"])
async def test_invitation_has_substantive_purpose(test_case):
    """Test that invitation purpose meets minimum length."""
    result = await _get_extraction_result(test_case)
    assert isinstance(result, Invitation)
    assert len(result.purpose) >= 10, f"purpose too short ({len(result.purpose)} chars): {result.purpose}"


@pytest.mark.parametrize("test_case", _INVITATION_CASES, ids=lambda x: x["email_id"])
async def test_invitation_has_substantive_summary(test_case):
    """Test that invitation event_summary meets minimum length."""
    result = await _get_extraction_result(test_case)
    assert isinstance(result, Invitation)
    assert len(result.event_summary) >= 10, (
        f"event_summary too short ({len(result.event_summary)} chars): {result.event_summary}"
    )


@pytest.mark.parametrize("test_case", _INVITATION_CASES, ids=lambda x: x["email_id"])
async def test_invitation_event_type_is_valid(test_case):
    """Test that the event_type is a valid EventType enum member."""
    result = await _get_extraction_result(test_case)
    assert isinstance(result, Invitation)
    assert isinstance(result.event_type, EventType), f"event_type is not EventType: {result.event_type}"


@pytest.mark.parametrize("test_case", _INVITATION_CASES, ids=lambda x: x["email_id"])
async def test_invitation_confidence_in_range(test_case):
    """Test that overall_confidence is between 0.0 and 1.0."""
    result = await _get_extraction_result(test_case)
    assert isinstance(result, Invitation)
    if result.overall_confidence is not None:
        assert 0.0 <= result.overall_confidence <= 1.0, f"overall_confidence out of range: {result.overall_confidence}"


# ============================================================================
# Structural Tests -- NotInvitation Results
# ============================================================================


@pytest.mark.parametrize("test_case", _NOT_INVITATION_CASES, ids=lambda x: x["email_id"])
async def test_not_invitation_has_substantive_reason(test_case):
    """Test that non-invitation reason meets minimum length."""
    result = await _get_extraction_result(test_case)
    assert isinstance(result, NotInvitation)
    assert len(result.reason) >= 10, f"reason too short ({len(result.reason)} chars): {result.reason}"
