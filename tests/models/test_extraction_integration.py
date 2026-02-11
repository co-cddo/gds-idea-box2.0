"""
Integration tests for invitation extraction using ground truth dataset.
Validates extraction accuracy using fuzzy matching.
"""

from typing import Any

import pandas as pd
import pytest
from fuzzywuzzy import fuzz

from invitation_triage.invitation_extraction import extract_invitation
from invitation_triage.models import Invitation, SafeDocument
from invitation_triage.models.document import generate_document_id
from tests.test_emails_dataset import TEST_EMAILS

# ============================================================================
# Helper Functions
# ============================================================================


def normalise_date(date_str: Any) -> str | None:
    """Normalise date to YYYY-MM-DD format, anchoring to 2026 if year is missing."""
    if pd.isna(date_str) or date_str is None:
        return None
    try:
        dt = pd.to_datetime(date_str)
        # If the parser defaults to year 1 (missing year in string)
        if dt.year == 1:
            dt = dt.replace(year=2026)
        return dt.strftime("%Y-%m-%d")
    except:
        return None


def fuzzy_match(expected: str | None, actual: str | None, threshold: int = 85) -> bool:
    """Check if two strings match using fuzzy logic."""
    if not expected and not actual:
        return True
    if not expected or not actual:
        return False
    return fuzz.partial_ratio(str(expected).lower(), str(actual).lower()) >= threshold


def topics_recall_sufficient(
    expected: list[str], actual: list[str], threshold: float = 0.5
) -> bool:
    """Check if the recall of extracted topics meets the required threshold."""
    if not expected:
        return True
    if not actual:
        return False

    expected_list = [t.lower().strip() for t in expected]
    actual_list = [t.lower().strip() for t in actual]

    matches = 0
    for exp in expected_list:
        for act in actual_list:
            # Use fuzzy match for individual topics
            if fuzz.ratio(exp, act) >= 80 or exp in act or act in exp:
                matches += 1
                break

    recall = matches / len(expected_list)
    return recall >= threshold


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


# ============================================================================
# Classification Tests
# ============================================================================


@pytest.mark.anyio
@pytest.mark.parametrize("test_case", TEST_EMAILS, ids=lambda x: x["email_id"])
async def test_classification_accuracy(test_case):
    """Test that each email is correctly classified as invitation or not."""
    safe_doc = create_safe_document_from_test(test_case)
    result = await extract_invitation(safe_doc)

    expected_is_invitation = test_case["is_invitation"]
    actual_is_invitation = isinstance(result, Invitation)

    assert expected_is_invitation == actual_is_invitation, (
        f"Classification failed for {test_case['email_id']}. "
        f"Expected: {expected_is_invitation}, Got: {actual_is_invitation}"
    )


# ============================================================================
# Field Extraction Tests (Fuzzy/Threshold Based)
# ============================================================================


@pytest.mark.anyio
@pytest.mark.parametrize(
    "test_case",
    [tc for tc in TEST_EMAILS if tc["is_invitation"]],
    ids=lambda x: x["email_id"],
)
async def test_invitation_field_integrity(test_case):
    """Test that invitation fields match ground truth using fuzzy logic."""
    safe_doc = create_safe_document_from_test(test_case)
    result = await extract_invitation(safe_doc)

    assert isinstance(result, Invitation)

    # 1. Event Type Strict Match
    if test_case.get("expected_event_type"):
        actual_type = (
            result.event_type.value
            if hasattr(result.event_type, "value")
            else str(result.event_type)
        )
        assert actual_type == test_case["expected_event_type"], (
            f"Event type mismatch: expected {test_case['expected_event_type']}, got {actual_type}"
        )

    # 2. Host Organisation Fuzzy Match
    if test_case.get("expected_host_org"):
        assert fuzzy_match(test_case["expected_host_org"], result.host_org), (
            f"Host organisation mismatch: expected {test_case['expected_host_org']}, got {result.host_org}"
        )

    # 3. Date Normalisation Match
    if test_case.get("expected_date"):
        expected_date = normalise_date(test_case["expected_date"])
        # Extract date from proposed_times
        actual_date = None
        if result.proposed_times:
            for time_str in result.proposed_times:
                parsed = normalise_date(time_str)
                if parsed:
                    actual_date = parsed
                    break

        assert actual_date == expected_date, (
            f"Date mismatch: expected {expected_date}, got {actual_date}"
        )

    # 4. Location Fuzzy Match
    if test_case.get("expected_location"):
        assert fuzzy_match(test_case["expected_location"], result.location), (
            f"Location mismatch: expected {test_case['expected_location']}, got {result.location}"
        )

    # 5. Topic Recall (50% threshold)
    if test_case.get("expected_topics"):
        assert topics_recall_sufficient(
            test_case["expected_topics"], result.topics or []
        ), f"Topic recall below 50% for {test_case['email_id']}"
