"""
Integration tests for invitation triage using ground truth dataset.
Validates triage accuracy: decision classification and priority assignment.

Results are cached per test case so each invitation is triaged once,
reducing LLM calls and ensuring consistency across decision, priority,
and calendar assertions for the same case.

Use pytest tests/integration/triage/test_triage.py --tb=short to show only output text
"""

import pytest

from box2.triage.models import MinisterPersona, TriagedDecision
from box2.triage.triage import triage_invitation
from tests.unit.triage.test_triage_dataset import TEST_PERSONA, TRIAGE_TEST_CASES

pytestmark = [pytest.mark.integration, pytest.mark.anyio]


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def minister_persona() -> MinisterPersona:
    """Create MinisterPersona from test data."""
    return MinisterPersona(**TEST_PERSONA)


# Cache triage results so each invitation is only triaged once.
# This avoids redundant LLM calls and ensures the decision, priority,
# and calendar tests all evaluate the same output.
_triage_cache: dict[str, TriagedDecision] = {}


async def _get_triage_result(test_case: dict, persona: MinisterPersona) -> TriagedDecision:
    """Return a cached triage result, calling the LLM only on first access."""
    test_id = test_case["test_id"]
    if test_id not in _triage_cache:
        _triage_cache[test_id] = await triage_invitation(test_case["invitation"], persona)
    return _triage_cache[test_id]


# ============================================================================
# Triage Accuracy Tests
# ============================================================================


@pytest.mark.parametrize("test_case", TRIAGE_TEST_CASES, ids=lambda x: x["test_id"])
async def test_triage_decision(test_case, minister_persona):
    """Test that each invitation receives an acceptable decision."""
    expected_decision = test_case["expected"]["decision"]
    acceptable = test_case["expected"].get("acceptable_decisions", [expected_decision])

    result = await _get_triage_result(test_case, minister_persona)

    assert result.decision.lower() in [d.lower() for d in acceptable], (
        f"Decision mismatch: expected one of {acceptable}, got {result.decision}\nLLM Reasoning: {result.reason}"
    )


@pytest.mark.parametrize("test_case", TRIAGE_TEST_CASES, ids=lambda x: x["test_id"])
async def test_triage_priority(test_case, minister_persona):
    """Test that each invitation receives the correct priority level."""
    expected_priority = test_case["expected"]["priority"]

    result = await _get_triage_result(test_case, minister_persona)

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
    result = await _get_triage_result(test_case, minister_persona)

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
