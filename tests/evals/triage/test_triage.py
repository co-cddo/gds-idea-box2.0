"""
Evals for triage decision and priority quality.

These assess LLM output quality for decision classification and priority
assignment. Some failure is expected -- these measure quality trends, not
correctness.

Results are cached per test case so each invitation is triaged once,
reducing LLM calls and ensuring consistency across decision and priority
assertions for the same case.

Run explicitly: AWS_PROFILE=bedrock-dev uv run pytest -m eval tests/evals/ -v
"""

import pytest

from box2.triage.models import MinisterPersona, TriagedDecision
from box2.triage.triage import triage_invitation
from tests.unit.triage.test_triage_dataset import TEST_PERSONA, TRIAGE_TEST_CASES

pytestmark = [pytest.mark.eval, pytest.mark.integration, pytest.mark.anyio]


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
# Decision Quality Evals
# ============================================================================


@pytest.mark.parametrize("test_case", TRIAGE_TEST_CASES, ids=lambda x: x["test_id"])
async def test_triage_decision(test_case, minister_persona):
    """Eval that each invitation receives an acceptable decision."""
    expected_decision = test_case["expected"]["decision"]
    acceptable = test_case["expected"].get("acceptable_decisions", [expected_decision])

    result = await _get_triage_result(test_case, minister_persona)

    assert result.decision.lower() in [d.lower() for d in acceptable], (
        f"Decision mismatch: expected one of {acceptable}, got {result.decision}\nLLM Reasoning: {result.reason}"
    )


@pytest.mark.parametrize("test_case", TRIAGE_TEST_CASES, ids=lambda x: x["test_id"])
async def test_triage_priority(test_case, minister_persona):
    """Eval that each invitation receives the correct priority level."""
    expected_priority = test_case["expected"]["priority"]

    result = await _get_triage_result(test_case, minister_persona)

    assert result.priority.lower() == expected_priority.lower(), (
        f"Priority mismatch: expected {expected_priority}, got {result.priority}\nLLM Reasoning: {result.reason}"
    )
