"""
Test of submission extraction from text.

Usage:
    uv run python scripts/example_submission_extraction.py
"""

import asyncio
import logging
from datetime import datetime

from invitation_triage.models import NotSubmission, SafeDocument
from invitation_triage.submission_extraction import extract_submission


async def main():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Sample submission text (from plan example)
    submission_text = """
MINISTERIAL SUBMISSION

URGENT SUBMISSION: AI Safety Institute Additional Funding

DATE: 4 February 2026

Minister,

Following the international AI summit, we urgently need approval for £3M additional
funding to the AI Safety Institute to maintain UK leadership position.

RECOMMENDATION: Approve £3M from contingency reserve

DECISION REQUIRED BY: 7 February 2026 (Treasury deadline)

KEY DATES:
- 10 Feb: International announcement
- 15 Feb: Contracts must be signed

POLICY AREA: AI Safety and International Collaboration

BACKGROUND:
UK committed to safety leadership at summit. Five other countries have announced
similar investments. Delay risks reputational damage and loss of research talent.

RISKS:
- If declined: International credibility hit, researchers may leave
- If approved: Need to find savings elsewhere in R&D budget

RELATED ITEMS:
- Previous contingency draw-down for quantum centre (Oct 2025)

Jane Smith, Deputy Director - AI Policy
DSIT
"""

    print("=" * 80)
    print("SUBMISSION EXTRACTION TEST")
    print("=" * 80)
    print(f"\nDocument preview: {submission_text[:100]}...")

    # Create SafeDocument
    print("\n📄 Creating SafeDocument...")
    safe_doc = SafeDocument(
        document_id="test-submission-1",
        filename="urgent_submission.txt",
        source_type="txt",
        safe_text=submission_text,
        document_timestamp=datetime.now(),
        pii_extracted={"emails": [], "phone_numbers": []},
        links_extracted=[],
    )
    print(f"   - Document ID: {safe_doc.document_id}")
    print(f"   - Source: {safe_doc.source_type}")

    # Extract submission
    print("\n🤖 Extracting submission details with LLM...")
    result = await extract_submission(safe_doc)

    # Display results
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)

    if isinstance(result, NotSubmission):
        print("\n❌ NOT A SUBMISSION")
        print(f"Reason: {result.reason}")
        if result.suggested_category:
            print(f"Suggested Category: {result.suggested_category}")
    else:
        print("\n✅ SUBMISSION DETECTED")
        print(f"\nSubmission ID: {result.submission_id}")
        print(f"Policy Area: {result.policy_area}")
        print(f"Responsible Official: {result.responsible_deputy_director}")
        print(f"Urgency: {result.urgency_assessment}")
        print(f"Decision Deadline: {result.decision_deadline}")
        print(f"\nOfficial Recommendation: {result.official_recommendation}")

        if result.required_decisions:
            print("\nRequired Decisions:")
            for decision in result.required_decisions:
                print(f"   - {decision}")

        if result.key_dates:
            print("\nKey Dates:")
            for date in result.key_dates:
                print(f"   - {date}")

        if result.related_items:
            print("\nRelated Items:")
            for item in result.related_items:
                print(f"   - {item}")

        print(f"\nSummary:\n{result.summary}")

        print(f"\n✉️  Draft Response:")
        print("-" * 80)
        print(result.draft_response)
        print("-" * 80)

        if result.overall_confidence:
            print(f"\nConfidence: {result.overall_confidence:.2f}")

    # Test a second example: routine submission
    print("\n\n" + "=" * 80)
    print("TEST 2: ROUTINE SUBMISSION")
    print("=" * 80)

    routine_text = """
MINISTERIAL SUBMISSION

Horizon Europe Quarterly Review - Q4 2025

DATE: 3 February 2026

Minister,

This submission provides Q4 2025 Horizon Europe participation data for your information.

SUMMARY: UK participation steady at 8.3% of projects. Strong performance in
health, quantum, and climate research. No significant issues identified.

RECOMMENDATION: Note the report; maintain current approach

POLICY AREA: International science collaboration

KEY METRICS:
- Total projects: 145 (vs 142 Q3)
- Success rate: 28.3% (EU average: 26.1%)
- Funding secured: €42M

FOR INFORMATION - No urgent action required

Next quarterly review: April 2026

RELATED ITEMS:
- Q3 2025 quarterly review
- Annual Horizon Europe strategy (January 2025)

Michael Brown, Deputy Director - International Research
DSIT
"""

    print(f"\nDocument preview: {routine_text[:100]}...")

    # Create SafeDocument
    print("\n📄 Creating SafeDocument...")
    safe_doc2 = SafeDocument(
        document_id="test-submission-2",
        filename="routine_submission.txt",
        source_type="txt",
        safe_text=routine_text,
        document_timestamp=datetime.now(),
        pii_extracted={"emails": [], "phone_numbers": []},
        links_extracted=[],
    )

    print("\n🤖 Extracting submission details with LLM...")
    result2 = await extract_submission(safe_doc2)

    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)

    if isinstance(result2, NotSubmission):
        print("\n❌ NOT A SUBMISSION")
        print(f"Reason: {result2.reason}")
    else:
        print("\n✅ SUBMISSION DETECTED")
        print(f"\nSubmission ID: {result2.submission_id}")
        print(f"Policy Area: {result2.policy_area}")
        print(f"Responsible Official: {result2.responsible_deputy_director}")
        print(f"Urgency: {result2.urgency_assessment}")
        print(f"Official Recommendation: {result2.official_recommendation}")
        print(f"\nSummary:\n{result2.summary}")

        print(f"\n✉️  Draft Response:")
        print("-" * 80)
        print(result2.draft_response)
        print("-" * 80)

    # Test a third example: not a submission (invitation)
    print("\n\n" + "=" * 80)
    print("TEST 3: NOT A SUBMISSION (INVITATION)")
    print("=" * 80)

    invitation_text = """
Dear Minister,

The Royal Society cordially invites you to deliver the keynote address at our
Annual Science Policy Conference on 15 March 2026 at 14:00.

The conference brings together 200+ senior researchers, industry leaders, and
policymakers to discuss the UK's strategic direction in science and innovation.

Your recent work on AI governance makes you an ideal speaker for our session on
"Technology and Society: Navigating the Next Decade".

Location: The Royal Society, Carlton House Terrace, London
Duration: 45-minute keynote + 15-minute Q&A

Please confirm by 1 March 2026.

Best regards,
Prof. Sarah Johnson
Chief Executive, The Royal Society
"""

    print(f"\nDocument preview: {invitation_text[:100]}...")

    # Create SafeDocument
    print("\n📄 Creating SafeDocument...")
    safe_doc3 = SafeDocument(
        document_id="test-invitation-1",
        filename="not_a_submission.txt",
        source_type="txt",
        safe_text=invitation_text,
        document_timestamp=datetime.now(),
        pii_extracted={"emails": [], "phone_numbers": []},
        links_extracted=[],
    )

    print("\n🤖 Extracting submission details with LLM...")
    result3 = await extract_submission(safe_doc3)

    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)

    if isinstance(result3, NotSubmission):
        print("\n❌ NOT A SUBMISSION")
        print(f"Reason: {result3.reason}")
        if result3.suggested_category:
            print(f"Suggested Category: {result3.suggested_category}")
    else:
        print("\n✅ SUBMISSION DETECTED")
        print("(This shouldn't happen - the document is an invitation!)")

    print("\n" + "=" * 80)
    print("ALL TESTS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
