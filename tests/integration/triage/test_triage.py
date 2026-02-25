"""
Integration tests for invitation triage.

These are deterministic tests that verify the LLM produces structurally
valid output and considers calendar context when expected. They should
pass consistently at temperature 0.3.

Results are cached per test case so each invitation is triaged once.

Run: AWS_PROFILE=bedrock-dev uv run pytest tests/integration/triage/test_triage.py -v
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
_triage_cache: dict[str, TriagedDecision] = {}


async def _get_triage_result(test_case: dict, persona: MinisterPersona) -> TriagedDecision:
    """Return a cached triage result, calling the LLM only on first access."""
    test_id = test_case["test_id"]
    if test_id not in _triage_cache:
        _triage_cache[test_id] = await triage_invitation(test_case["invitation"], persona)
    return _triage_cache[test_id]


# ============================================================================
# Structural Tests
# ============================================================================


@pytest.mark.parametrize("test_case", TRIAGE_TEST_CASES, ids=lambda x: x["test_id"])
async def test_triage_decision_is_valid(test_case, minister_persona):
    """Test that the decision is one of the five allowed values."""
    result = await _get_triage_result(test_case, minister_persona)

    valid_decisions = {"accept", "decline", "delegate", "request_more_info", "defer"}
    assert result.decision in valid_decisions, f"Invalid decision: {result.decision}, expected one of {valid_decisions}"


@pytest.mark.parametrize("test_case", TRIAGE_TEST_CASES, ids=lambda x: x["test_id"])
async def test_triage_priority_is_valid(test_case, minister_persona):
    """Test that the priority is one of the three allowed values."""
    result = await _get_triage_result(test_case, minister_persona)

    valid_priorities = {"high", "medium", "low"}
    assert result.priority in valid_priorities, (
        f"Invalid priority: {result.priority}, expected one of {valid_priorities}"
    )


@pytest.mark.parametrize("test_case", TRIAGE_TEST_CASES, ids=lambda x: x["test_id"])
async def test_triage_has_substantive_reason(test_case, minister_persona):
    """Test that the triage reason meets minimum length."""
    result = await _get_triage_result(test_case, minister_persona)

    assert len(result.reason) >= 10, f"reason too short ({len(result.reason)} chars): {result.reason}"


@pytest.mark.parametrize("test_case", TRIAGE_TEST_CASES, ids=lambda x: x["test_id"])
async def test_triage_has_substantive_draft_response(test_case, minister_persona):
    """Test that the draft response meets minimum length."""
    result = await _get_triage_result(test_case, minister_persona)

    assert len(result.draft_response) >= 20, (
        f"draft_response too short ({len(result.draft_response)} chars): {result.draft_response}"
    )


# ============================================================================
# Calendar Consideration Tests
# ============================================================================


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
