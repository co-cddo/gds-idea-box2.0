"""
Test of response redrafting and submission reply generation.

Shows how:
- Invitation drafts are modified by LLM based on office notes
- Submission replies are generated formulaically from minister's response

Usage:
    uv run python scripts/example_redraft.py
"""

import asyncio
import logging

from box2.triage.invitation_redraft import redraft_invitation_response
from box2.triage.models import Submission, SubmissionResponse, TriagedDecision
from box2.triage.submission_reply import generate_submission_reply


async def main():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    print("=" * 80)
    print("RESPONSE GENERATION TEST")
    print("=" * 80)

    # ========================================================================
    # TEST 1: Invitation - Conditional Acceptance (LLM redraft)
    # ========================================================================

    print("\n" + "=" * 80)
    print("TEST 1: INVITATION - CONDITIONAL ACCEPTANCE (LLM redraft)")
    print("=" * 80)

    original_invitation_draft = """Dear Dr Chen,

Thank you for your invitation to the AI Safety Summit reception on 15 February 2026. I would be delighted to attend the event at The Royal Society from 6:00 PM to 8:00 PM.

This is an important opportunity to engage with leading AI researchers and discuss the UK's ongoing commitment to AI safety.

Best regards"""

    office_notes_1 = "Can only attend from 7pm onwards due to Cabinet committee"

    print("\n ORIGINAL DRAFT:")
    print("-" * 80)
    print(original_invitation_draft)
    print("-" * 80)

    print(f"\n OFFICE NOTES: {office_notes_1}")

    # Create mock source for context (would normally come from triage)
    mock_decision = TriagedDecision(
        document_id="test-001",
        decision="accept",
        priority="high",
        reason="AI safety aligns with minister's priorities",
        draft_response=original_invitation_draft,
    )

    print("\n Redrafting invitation response...")
    redrafted_1 = await redraft_invitation_response(
        original_draft=original_invitation_draft,
        office_notes=office_notes_1,
        source=mock_decision,
    )

    print("\n REDRAFTED RESPONSE:")
    print("-" * 80)
    print(redrafted_1)
    print("-" * 80)

    # ========================================================================
    # TEST 2: Submission - Minister's Response (template-based)
    # ========================================================================

    print("\n\n" + "=" * 80)
    print("TEST 2: SUBMISSION - REDUCED APPROVAL (template reply)")
    print("=" * 80)

    mock_submission = Submission(
        document_id="SUB-TEST-001",
        policy_area="AI Safety and International Collaboration",
        responsible_deputy_director="Jane Smith, Deputy Director - AI Policy",
        summary="Request for £3M additional funding for AI Safety Institute",
        official_recommendation="Approve £3M from contingency reserve",
        urgency_assessment="urgent",
        decision_deadline="7 February 2026",
    )

    submission_response_2 = SubmissionResponse(
        document_id="SUB-TEST-001",
        minister_response="Approve £2M only, not £3M. Request revised project scope.",
    )

    print(f"\n MINISTER'S RESPONSE: {submission_response_2.minister_response}")

    reply_2 = generate_submission_reply(
        submission=mock_submission,
        response=submission_response_2,
    )

    print("\n SUBMISSION REPLY:")
    print("-" * 80)
    print(reply_2.reply_text)
    print("-" * 80)

    # ========================================================================
    # TEST 3: Submission - Request More Info (template-based)
    # ========================================================================

    print("\n\n" + "=" * 80)
    print("TEST 3: SUBMISSION - REQUEST MORE INFO (template reply)")
    print("=" * 80)

    mock_submission_3 = Submission(
        document_id="SUB-TEST-002",
        policy_area="AI Safety and International Collaboration",
        responsible_deputy_director="Jane Smith, Deputy Director - AI Policy",
        summary="Request for £3M additional funding for AI Safety Institute",
        official_recommendation="Approve £3M from contingency reserve",
        urgency_assessment="urgent",
        decision_deadline="7 February 2026",
    )

    submission_response_3 = SubmissionResponse(
        document_id="SUB-TEST-002",
        minister_response="Need more detail on international partner commitments before approving. "
        "Please provide a breakdown of partner contributions and timelines.",
    )

    print(f"\n MINISTER'S RESPONSE: {submission_response_3.minister_response}")

    reply_3 = generate_submission_reply(
        submission=mock_submission_3,
        response=submission_response_3,
    )

    print("\n SUBMISSION REPLY:")
    print("-" * 80)
    print(reply_3.reply_text)
    print("-" * 80)

    print("\n" + "=" * 80)
    print("All response generation tests complete!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
