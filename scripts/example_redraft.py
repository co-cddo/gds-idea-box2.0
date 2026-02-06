"""
Test of response redrafting.

Shows how original drafts are modified based on office notes.

Usage:
    uv run python scripts/example_redraft.py
"""

import asyncio
import logging

from invitation_triage.models import Submission, TriagedDecision
from invitation_triage.redraft import redraft_response


async def main():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    print("=" * 80)
    print("REDRAFT RESPONSE TEST")
    print("=" * 80)

    # ========================================================================
    # TEST 1: Invitation - Conditional Acceptance
    # ========================================================================

    print("\n" + "=" * 80)
    print("TEST 1: INVITATION - CONDITIONAL ACCEPTANCE")
    print("=" * 80)

    original_invitation_draft = """Dear Dr Chen,

Thank you for your invitation to the AI Safety Summit reception on 15 February 2026. I would be delighted to attend the event at The Royal Society from 6:00 PM to 8:00 PM.

This is an important opportunity to engage with leading AI researchers and discuss the UK's ongoing commitment to AI safety.

Best regards"""

    office_notes_1 = "Can only attend from 7pm onwards due to Cabinet committee"

    print("\n📄 ORIGINAL DRAFT:")
    print("-" * 80)
    print(original_invitation_draft)
    print("-" * 80)

    print(f"\n📝 OFFICE NOTES: {office_notes_1}")

    # Create mock source for context (would normally come from triage)
    mock_decision = TriagedDecision(
        email_id="test-001",
        decision="accept",
        priority="high",
        reason="AI safety aligns with minister's priorities",
        draft_response=original_invitation_draft,
    )

    print("\n🤖 Redrafting response...")
    redrafted_1 = await redraft_response(
        original_draft=original_invitation_draft,
        office_notes=office_notes_1,
        source=mock_decision,
        document_type="invitation",
    )

    print("\n✉️  REDRAFTED RESPONSE:")
    print("-" * 80)
    print(redrafted_1)
    print("-" * 80)

    # ========================================================================
    # TEST 2: Submission - Reduced Approval
    # ========================================================================

    print("\n\n" + "=" * 80)
    print("TEST 2: SUBMISSION - REDUCED APPROVAL")
    print("=" * 80)

    original_submission_draft = """I approve the £3M funding from contingency reserve as recommended. Please proceed with Treasury notifications by the 7 February deadline and ensure contracts are signed by 15 February."""

    office_notes_2 = "Approve £2M only, not the full £3M. Request revised project scope"

    print("\n📄 ORIGINAL DRAFT:")
    print("-" * 80)
    print(original_submission_draft)
    print("-" * 80)

    print(f"\n📝 OFFICE NOTES: {office_notes_2}")

    # Create mock submission for context
    mock_submission = Submission(
        submission_id="SUB-TEST-001",
        policy_area="AI Safety and International Collaboration",
        responsible_deputy_director="Jane Smith, Deputy Director - AI Policy",
        summary="Request for £3M additional funding for AI Safety Institute",
        official_recommendation="Approve £3M from contingency reserve",
        urgency_assessment="urgent",
        decision_deadline="7 February 2026",
        draft_response=original_submission_draft,
    )

    print("\n🤖 Redrafting response...")
    redrafted_2 = await redraft_response(
        original_draft=original_submission_draft,
        office_notes=office_notes_2,
        source=mock_submission,
        document_type="submission",
    )

    print("\n✉️  REDRAFTED RESPONSE:")
    print("-" * 80)
    print(redrafted_2)
    print("-" * 80)

    # ========================================================================
    # TEST 3: Submission - Request More Info
    # ========================================================================

    print("\n\n" + "=" * 80)
    print("TEST 3: SUBMISSION - REQUEST MORE INFO")
    print("=" * 80)

    original_submission_draft_3 = """I approve the £3M funding from contingency reserve as recommended. Please proceed with Treasury notifications by the 7 February deadline."""

    office_notes_3 = (
        "Need more detail on international partner commitments before approving"
    )

    print("\n📄 ORIGINAL DRAFT:")
    print("-" * 80)
    print(original_submission_draft_3)
    print("-" * 80)

    print(f"\n📝 OFFICE NOTES: {office_notes_3}")

    mock_submission_3 = Submission(
        submission_id="SUB-TEST-002",
        policy_area="AI Safety and International Collaboration",
        responsible_deputy_director="Jane Smith, Deputy Director - AI Policy",
        summary="Request for £3M additional funding for AI Safety Institute",
        official_recommendation="Approve £3M from contingency reserve",
        urgency_assessment="urgent",
        decision_deadline="7 February 2026",
        draft_response=original_submission_draft_3,
    )

    print("\n🤖 Redrafting response...")
    redrafted_3 = await redraft_response(
        original_draft=original_submission_draft_3,
        office_notes=office_notes_3,
        source=mock_submission_3,
        document_type="submission",
    )

    print("\n✉️  REDRAFTED RESPONSE:")
    print("-" * 80)
    print(redrafted_3)
    print("-" * 80)

    print("\n" + "=" * 80)
    print("✨ All redraft tests complete!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
