"""
Integration tests for invitation triage using ground truth dataset.
Validates triage accuracy: decision classification and priority assignment.

Use pytest tests/integration/triage/test_triage.py --tb=short to avoid replication of the code and show only output text
"""

import pytest

from box2.triage.models import MinisterPersona
from box2.triage.triage import triage_invitation
from tests.unit.triage.test_triage_dataset import TEST_PERSONA, TRIAGE_TEST_CASES

pytestmark = [pytest.mark.integration, pytest.mark.anyio]


@pytest.fixture
def minister_persona() -> MinisterPersona:
    """Create MinisterPersona from test data."""
    return MinisterPersona(**TEST_PERSONA)


# ============================================================================
# Triage Accuracy Tests
# ============================================================================


@pytest.mark.parametrize("test_case", TRIAGE_TEST_CASES, ids=lambda x: x["test_id"])
async def test_triage_decision(test_case, minister_persona):
    """Test that each invitation receives the correct decision."""

    invitation = test_case["invitation"]
    expected_decision = test_case["expected"]["decision"]

    result = await triage_invitation(invitation, minister_persona)

    assert result.minister_decision.lower() == expected_decision.lower(), (
        f"Decision mismatch: expected {expected_decision}, got {result.minister_decision}\nLLM Reasoning: {result.reason}"
    )


@pytest.mark.parametrize("test_case", TRIAGE_TEST_CASES, ids=lambda x: x["test_id"])
async def test_triage_priority(test_case, minister_persona):
    """Test that each invitation receives the correct priority level."""

    invitation = test_case["invitation"]
    expected_priority = test_case["expected"]["priority"]

    result = await triage_invitation(invitation, minister_persona)

    assert result.priority.lower() == expected_priority.lower(), (
        f"Priority mismatch: expected {expected_priority}, got {result.priority}\nLLM Reasoning: {result.reason}"
    )


@pytest.mark.parametrize(
    "test_case",
    [tc for tc in TRIAGE_TEST_CASES if tc["expected"].get("should_mention_calendar", False)],
    ids=lambda x: x["test_id"],
)
async def test_triage_calendar_consideration(test_case, minister_persona):
    """Test that calendar conflicts are mentioned in reasoning when expected."""

    invitation = test_case["invitation"]

    result = await triage_invitation(invitation, minister_persona)

    calendar_keywords = [
        "calendar",
        "schedule",
        "conflict",
        "available",
        "clash",
        "timing",
        "slot",
        "commitment",
        "meeting",
    ]

    mentions_calendar = any(keyword in result.reason.lower() for keyword in calendar_keywords)

    assert mentions_calendar, f"Calendar conflicts exist but not mentioned in reasoning\nLLM Reasoning: {result.reason}"
