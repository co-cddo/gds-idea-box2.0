"""
Test of complete action extraction flow.

Shows the full workflow from office response to extracted actions.

Usage:
    uv run python scripts/example_action_extraction.py
"""

import asyncio
import json
import logging
from datetime import datetime

from invitation_triage.action_extraction import extract_actions
from invitation_triage.models import (
    DocumentClassification,
    OfficeResponse,
    SafeDocument,
    Submission,
    TriagedDecision,
)
from invitation_triage.redraft import redraft_response


async def main():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    print("=" * 80)
    print("ACTION EXTRACTION TEST")
    print("=" * 80)

    # ========================================================================
    # TEST 1: Invitation - Accept with Modification
    # ========================================================================

    print("\n" + "=" * 80)
    print("TEST 1: INVITATION - ACCEPT WITH MODIFICATION")
    print("=" * 80)

    # Mock SafeDocument
    safe_doc_1 = SafeDocument(
        document_id="invite-001",
        filename="ai_safety_invite.eml",
        source_type="email",
        safe_text="AI Safety Summit reception invitation...",
        document_timestamp=datetime.now(),
        pii_extracted={"emails": [], "phone_numbers": []},
        links_extracted=[],
    )

    # Mock Classification
    classification_1 = DocumentClassification(
        document_id="invite-001",
        document_type="invitation",
        confidence=0.95,
        reasoning="Clear invitation to event",
    )

    # Mock TriagedDecision
    original_draft_1 = """Dear Dr Chen,

Thank you for your invitation to the AI Safety Summit reception on 15 February 2026. I would be delighted to attend the event at The Royal Society from 6:00 PM to 8:00 PM.

This is an important opportunity to engage with leading AI researchers.

Best regards"""

    triaged_1 = TriagedDecision(
        email_id="invite-001",
        decision="accept",
        priority="high",
        reason="AI safety aligns with priorities",
        draft_response=original_draft_1,
    )

    # Office Response - "yes_but" with modification
    office_response_1 = OfficeResponse(
        document_id="invite-001",
        document_type="invitation",
        decision="yes_but",
        notes="Can only attend from 7pm onwards due to Cabinet committee",
    )

    print("\n📝 OFFICE RESPONSE:")
    print(f"   Decision: {office_response_1.decision}")
    print(f"   Notes: {office_response_1.notes}")

    # Redraft the response
    print("\n🤖 Redrafting response based on office notes...")
    final_draft_1 = await redraft_response(
        original_draft=original_draft_1,
        office_notes=office_response_1.notes,
        source=triaged_1,
        document_type="invitation",
    )

    print("\n✉️  REDRAFTED RESPONSE:")
    print("-" * 80)
    print(final_draft_1)
    print("-" * 80)

    # Extract actions
    print("\n🤖 Extracting actions...")
    result_1 = await extract_actions(
        document=safe_doc_1,
        classification=classification_1,
        source=triaged_1,
        office_response=office_response_1,
        final_draft=final_draft_1,
    )

    print("\n📋 EXTRACTED ACTIONS:")
    print(f"   Total Actions: {len(result_1.actions)}")
    print(f"   Summary: {result_1.summary}")
    print()

    for i, action in enumerate(result_1.actions, 1):
        print(f"\n   Action {i}:")
        print(f"     Type: {action.action_type}")
        print(f"     Description: {action.description}")
        print(f"     Urgency: {action.urgency}")
        if action.deadline:
            print(f"     Deadline: {action.deadline}")
        if action.owner:
            print(f"     Owner: {action.owner}")
        if action.draft_content:
            print(f"     Has Draft: Yes ({len(action.draft_content)} chars)")

    # ========================================================================
    # TEST 2: Submission - Approve with Reduced Amount
    # ========================================================================

    print("\n\n" + "=" * 80)
    print("TEST 2: SUBMISSION - APPROVE WITH REDUCED AMOUNT")
    print("=" * 80)

    # Mock SafeDocument
    safe_doc_2 = SafeDocument(
        document_id="sub-001",
        filename="funding_submission.txt",
        source_type="txt",
        safe_text="Ministerial submission requesting £3M funding...",
        document_timestamp=datetime.now(),
        pii_extracted={"emails": [], "phone_numbers": []},
        links_extracted=[],
    )

    # Mock Classification
    classification_2 = DocumentClassification(
        document_id="sub-001",
        document_type="submission",
        confidence=0.98,
        reasoning="Clear ministerial submission with recommendation",
    )

    # Mock Submission
    original_draft_2 = """I approve the £3M funding from contingency reserve as recommended. Please proceed with Treasury notifications by the 7 February deadline and ensure contracts are signed by 15 February."""

    submission_2 = Submission(
        submission_id="SUB-2026-001",
        policy_area="AI Safety and International Collaboration",
        responsible_deputy_director="Jane Smith, Deputy Director - AI Policy",
        summary="Request for £3M funding for AI Safety Institute",
        official_recommendation="Approve £3M from contingency reserve",
        urgency_assessment="urgent",
        decision_deadline="7 February 2026",
        draft_response=original_draft_2,
    )

    # Office Response - "yes_but" with reduced amount
    office_response_2 = OfficeResponse(
        document_id="sub-001",
        document_type="submission",
        decision="yes_but",
        notes="Approve £2M only, not £3M. Request revised project scope.",
    )

    print("\n📝 OFFICE RESPONSE:")
    print(f"   Decision: {office_response_2.decision}")
    print(f"   Notes: {office_response_2.notes}")

    # Redraft the response
    print("\n🤖 Redrafting response based on office notes...")
    final_draft_2 = await redraft_response(
        original_draft=original_draft_2,
        office_notes=office_response_2.notes,
        source=submission_2,
        document_type="submission",
    )

    print("\n✉️  REDRAFTED RESPONSE:")
    print("-" * 80)
    print(final_draft_2)
    print("-" * 80)

    # Extract actions
    print("\n🤖 Extracting actions...")
    result_2 = await extract_actions(
        document=safe_doc_2,
        classification=classification_2,
        source=submission_2,
        office_response=office_response_2,
        final_draft=final_draft_2,
    )

    print("\n📋 EXTRACTED ACTIONS:")
    print(f"   Total Actions: {len(result_2.actions)}")
    print(f"   Summary: {result_2.summary}")
    print()

    for i, action in enumerate(result_2.actions, 1):
        print(f"\n   Action {i}:")
        print(f"     Type: {action.action_type}")
        print(f"     Description: {action.description}")
        print(f"     Urgency: {action.urgency}")
        if action.deadline:
            print(f"     Deadline: {action.deadline}")
        if action.owner:
            print(f"     Owner: {action.owner}")
        if action.draft_content:
            print(f"     Has Draft: Yes ({len(action.draft_content)} chars)")

    # ========================================================================
    # TEST 3: Save Result as JSON
    # ========================================================================

    print("\n\n" + "=" * 80)
    print("SAVING RESULT AS JSON")
    print("=" * 80)

    # Convert to dict for JSON serialization
    result_dict = result_1.model_dump(mode="json")

    print("\n📄 JSON Output Preview:")
    print(json.dumps(result_dict, indent=2)[:500] + "...")

    print("\n" + "=" * 80)
    print("✨ All action extraction tests complete!")
    print("=" * 80)
    print("\n💾 Actions can be stored as JSON for tracking and execution.")


if __name__ == "__main__":
    asyncio.run(main())
