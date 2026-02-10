"""
Tests for submission reply generation.

Tests the template-based reply generator and associated models.
"""

import pytest
from pydantic import ValidationError

from invitation_triage.models import Submission, SubmissionReply, SubmissionResponse
from invitation_triage.submission_reply import generate_submission_reply

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_submission():
    """Provide a sample Submission for testing."""
    return Submission(
        submission_id="SUB-TEST-001",
        policy_area="AI Safety and International Collaboration",
        responsible_deputy_director="Jane Smith, Deputy Director - AI Policy",
        summary="Request for £3M additional funding for AI Safety Institute",
        official_recommendation="Approve £3M from contingency reserve",
        urgency_assessment="urgent",
        decision_deadline="7 February 2026",
        draft_response=(
            "I approve the £3M funding from contingency reserve as recommended."
        ),
    )


@pytest.fixture
def approval_response():
    """Minister approves with reduced amount."""
    return SubmissionResponse(
        submission_id="SUB-TEST-001",
        minister_response="Approve £2M only, not £3M. Request revised project scope.",
    )


@pytest.fixture
def rejection_response():
    """Minister rejects the submission."""
    return SubmissionResponse(
        submission_id="SUB-TEST-001",
        minister_response="Rejected - not a priority right now. Revisit in Q3.",
    )


@pytest.fixture
def info_request_response():
    """Minister requests more information."""
    return SubmissionResponse(
        submission_id="SUB-TEST-001",
        minister_response="Need more detail on international partner commitments "
        "before approving. Provide breakdown of contributions.",
    )


# ============================================================================
# SubmissionResponse Model Tests
# ============================================================================


def test_submission_response_creation():
    """Test creating a SubmissionResponse with required fields."""
    response = SubmissionResponse(
        submission_id="SUB-001",
        minister_response="Approved as recommended",
    )

    assert response.submission_id == "SUB-001"
    assert response.minister_response == "Approved as recommended"
    assert response.responded_by == "Private Office"
    assert response.responded_at is not None


def test_submission_response_custom_responder():
    """Test SubmissionResponse with custom responded_by."""
    response = SubmissionResponse(
        submission_id="SUB-001",
        minister_response="Approved",
        responded_by="PPS - John Davies",
    )

    assert response.responded_by == "PPS - John Davies"


def test_submission_response_empty_minister_response_rejected():
    """Test that empty minister_response is rejected by validation."""
    with pytest.raises(ValidationError):
        SubmissionResponse(
            submission_id="SUB-001",
            minister_response="",
        )


# ============================================================================
# SubmissionReply Model Tests
# ============================================================================


def test_submission_reply_creation():
    """Test creating a SubmissionReply with all fields."""
    reply = SubmissionReply(
        submission_id="SUB-001",
        policy_area="AI Safety",
        official_recommendation="Approve £3M",
        minister_response="Approve £2M only",
        reply_text="RE: AI Safety\n\nOfficial Recommendation:\nApprove £3M\n\n"
        "Minister's Response:\nApprove £2M only",
    )

    assert reply.submission_id == "SUB-001"
    assert reply.policy_area == "AI Safety"
    assert reply.official_recommendation == "Approve £3M"
    assert reply.minister_response == "Approve £2M only"
    assert reply.created_at is not None


def test_submission_reply_short_text_rejected():
    """Test that reply_text below min_length is rejected."""
    with pytest.raises(ValidationError):
        SubmissionReply(
            submission_id="SUB-001",
            policy_area="AI",
            official_recommendation="Approve",
            minister_response="Yes",
            reply_text="Too short",
        )


# ============================================================================
# generate_submission_reply Tests
# ============================================================================


def test_generate_reply_contains_official_recommendation_verbatim(
    sample_submission, approval_response
):
    """Test that the official recommendation appears verbatim in reply."""
    reply = generate_submission_reply(sample_submission, approval_response)

    assert sample_submission.official_recommendation in reply.reply_text


def test_generate_reply_contains_minister_response_verbatim(
    sample_submission, approval_response
):
    """Test that the minister's response appears verbatim in reply."""
    reply = generate_submission_reply(sample_submission, approval_response)

    assert approval_response.minister_response in reply.reply_text


def test_generate_reply_contains_policy_area(sample_submission, approval_response):
    """Test that the policy area appears in reply."""
    reply = generate_submission_reply(sample_submission, approval_response)

    assert sample_submission.policy_area in reply.reply_text


def test_generate_reply_model_fields_match_inputs(sample_submission, approval_response):
    """Test that SubmissionReply fields match the input data."""
    reply = generate_submission_reply(sample_submission, approval_response)

    assert reply.submission_id == sample_submission.submission_id
    assert reply.policy_area == sample_submission.policy_area
    assert reply.official_recommendation == sample_submission.official_recommendation
    assert reply.minister_response == approval_response.minister_response


def test_generate_reply_with_rejection(sample_submission, rejection_response):
    """Test reply generation for a rejection."""
    reply = generate_submission_reply(sample_submission, rejection_response)

    assert rejection_response.minister_response in reply.reply_text
    assert sample_submission.official_recommendation in reply.reply_text


def test_generate_reply_with_info_request(sample_submission, info_request_response):
    """Test reply generation for a request for more information."""
    reply = generate_submission_reply(sample_submission, info_request_response)

    assert info_request_response.minister_response in reply.reply_text
    assert sample_submission.official_recommendation in reply.reply_text


def test_generate_reply_is_deterministic(sample_submission, approval_response):
    """Test that the same inputs produce the same output (no LLM randomness)."""
    reply_1 = generate_submission_reply(sample_submission, approval_response)
    reply_2 = generate_submission_reply(sample_submission, approval_response)

    assert reply_1.reply_text == reply_2.reply_text


def test_generate_reply_starts_with_re_prefix(sample_submission, approval_response):
    """Test that the reply text starts with RE: {policy_area}."""
    reply = generate_submission_reply(sample_submission, approval_response)

    expected_prefix = f"RE: {sample_submission.policy_area}"
    assert reply.reply_text.startswith(expected_prefix)


def test_generate_reply_has_section_headers(sample_submission, approval_response):
    """Test that the reply text contains the expected section headers."""
    reply = generate_submission_reply(sample_submission, approval_response)

    assert "Official Recommendation:" in reply.reply_text
    assert "Minister's Response:" in reply.reply_text


# ============================================================================
# Edge Cases
# ============================================================================


def test_generate_reply_with_long_minister_response(sample_submission):
    """Test reply generation with a very long minister response."""
    long_response = SubmissionResponse(
        submission_id="SUB-TEST-001",
        minister_response=(
            "I have several concerns about this proposal. First, the budget seems "
            "overly optimistic given current fiscal constraints. Second, I would like "
            "to see more detail on the international partner commitments, particularly "
            "from the US and Japan. Third, the timeline seems aggressive - can we "
            "explore a phased approach starting with £1M in Q1, reviewing before "
            "committing further funds? Please also consult with Treasury before "
            "proceeding. I want to see a revised proposal by end of month."
        ),
    )

    reply = generate_submission_reply(sample_submission, long_response)

    assert long_response.minister_response in reply.reply_text


def test_generate_reply_with_special_characters(sample_submission):
    """Test reply generation with special characters in minister response."""
    response = SubmissionResponse(
        submission_id="SUB-TEST-001",
        minister_response=(
            "Approve £2M (not £3M) - see note re: 'revised scope' & timeline"
        ),
    )

    reply = generate_submission_reply(sample_submission, response)

    assert response.minister_response in reply.reply_text


def test_generate_reply_with_different_submission():
    """Test reply generation with a different policy area."""
    submission = Submission(
        submission_id="SUB-TEST-002",
        policy_area="Quantum Technologies - National Programme",
        responsible_deputy_director="Bob Wilson, Deputy Director - Quantum",
        summary="Request for programme extension and additional funding",
        official_recommendation=(
            "Extend programme by 2 years with £5M additional funding"
        ),
        urgency_assessment="routine",
        draft_response=(
            "I approve the extension of the quantum programme as recommended."
        ),
    )

    response = SubmissionResponse(
        submission_id="SUB-TEST-002",
        minister_response="Approve 1 year extension only. Review again next year.",
    )

    reply = generate_submission_reply(submission, response)

    assert "Quantum Technologies - National Programme" in reply.reply_text
    assert "Extend programme by 2 years with £5M additional funding" in reply.reply_text
    assert "Approve 1 year extension only. Review again next year." in reply.reply_text
    assert reply.submission_id == "SUB-TEST-002"
