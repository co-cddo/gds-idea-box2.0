from datetime import date, datetime

import pytest
from pydantic import ValidationError

from src.box2.triage.models.parli_question_sharepoint import SharepointPQs

# Minimal kwargs for a valid SharepointPQs — only Parliament API fields + urgency.
_REQUIRED_FIELDS = {
    "title": "123456",
    "questiontext": "To ask the Secretary of State ...",
    "house": "commons",
    "datetabled": datetime(2026, 2, 24),
    "date_for_answer": datetime(2026, 2, 26),
    "asking_member_id": "5047",
    "answering_body_name": "Department for Science, Innovation and Technology",
    "asking_member_name": "Jane Smith MP",
    "urgency": "urgent",
    "is_named_day": False,
    "target_date": date(2026, 2, 25),
    "draft_due": date(2026, 2, 24),
    "spads": "With Spads",
    "officials": "With Officials",
    "notes": None,
}


def test_construct_with_required_fields_only():
    """SharepointPQs should be constructable with only Parliament API fields.

    AI-generated fields default to None, simulating a pipeline where
    routing or drafting failed for this UIN.
    """
    pq = SharepointPQs(**_REQUIRED_FIELDS)

    assert pq.title == "123456"
    assert pq.ai_expansive_answer is None
    assert pq.ai_generic_answer is None
    assert pq.ai_predicted_directorate is None
    assert pq.ai_predicted_scs is None
    assert pq.ai_routing_confidence is None
    assert pq.ai_routing_reasoning is None
    assert pq.ai_routing_alternative_directorate is None
    assert pq.url == []
    assert pq.minister_comment is None
    assert pq.minister_decision is None


def test_construct_with_all_fields():
    """SharepointPQs should accept all fields including AI-generated ones."""
    pq = SharepointPQs(
        **_REQUIRED_FIELDS,
        ai_expansive_answer="A detailed draft response covering the key policy points.",
        ai_generic_answer="A generic draft response for the parliamentary question.",
        url=["https://www.gov.uk/example"],
        ai_predicted_directorate="Science, Research & Innovation",
        ai_predicted_scs="Dr Sarah Chen, DD Science Funding",
        ai_routing_confidence="high",
        ai_routing_reasoning="Directly concerns STFC funding allocations.",
        ai_routing_alternative_directorate="Cross-Government S&T",
    )

    assert pq.ai_expansive_answer is not None
    assert pq.ai_predicted_directorate == "Science, Research & Innovation"
    assert len(pq.url) == 1


def test_invalid_house_rejected():
    """house must be 'commons' or 'lords'."""
    with pytest.raises(ValidationError):
        SharepointPQs(**{**_REQUIRED_FIELDS, "house": "senate"})


def test_invalid_urgency_rejected():
    """urgency must be 'urgent' or 'not urgent'."""
    with pytest.raises(ValidationError):
        SharepointPQs(**{**_REQUIRED_FIELDS, "urgency": "maybe"})


def test_invalid_minister_decision_rejected():
    """minister_decision must be 'approve', 'request redraft', or None."""
    with pytest.raises(ValidationError):
        SharepointPQs(**{**_REQUIRED_FIELDS, "minister_decision": "veto"})
