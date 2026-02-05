"""
Test of upload classification.

Usage:
    uv run python scripts/example_upload_classification.py
"""

import asyncio
import logging

from invitation_triage.models import ProcessedUpload
from invitation_triage.upload_classifier import classify_upload


async def main():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    print("=" * 80)
    print("UPLOAD CLASSIFICATION TEST")
    print("=" * 80)

    # Test 1: Invitation
    print("\n" + "=" * 80)
    print("TEST 1: INVITATION")
    print("=" * 80)

    invitation_text = """
Dear Minister,

The Royal Society cordially invites you to deliver the keynote address at our
Annual Science Policy Conference on 15 March 2026 at 14:00.

The conference brings together 200+ senior researchers, industry leaders, and
policymakers to discuss the UK's strategic direction in science and innovation.

Your recent work on AI governance makes you an ideal speaker for our session on
"Technology and Society: Navigating the Next Decade".

We would be honored by your participation.

Location: The Royal Society, Carlton House Terrace, London
Duration: 45-minute keynote + 15-minute Q&A
Suggested topics: AI policy, international collaboration, research funding

Please confirm by 1 March 2026.

Best regards,
Prof. Sarah Johnson
Chief Executive, The Royal Society
"""

    upload1 = ProcessedUpload(
        upload_id="TEST-001",
        text=invitation_text,
        source_type="email",
        subject="Invitation: Royal Society Annual Conference Keynote",
    )

    print(f"\nUpload ID: {upload1.upload_id}")
    print(f"Source: {upload1.source_type}")
    print(f"Subject: {upload1.subject}")
    print(f"\nText preview: {invitation_text[:150]}...")

    print("\n🤖 Classifying document...")
    result1 = await classify_upload(upload1)

    print("\n" + "-" * 80)
    print("CLASSIFICATION RESULT")
    print("-" * 80)
    print(f"Document Type: {result1.document_type}")
    print(f"Confidence: {result1.confidence:.2f}")
    print(f"Reasoning: {result1.reasoning}")

    # Test 2: Submission
    print("\n\n" + "=" * 80)
    print("TEST 2: MINISTERIAL SUBMISSION")
    print("=" * 80)

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

Jane Smith, Deputy Director - AI Policy
DSIT
"""

    upload2 = ProcessedUpload(
        upload_id="TEST-002",
        text=submission_text,
        source_type="pdf",
        filename="AI_Safety_Funding_Submission.pdf",
    )

    print(f"\nUpload ID: {upload2.upload_id}")
    print(f"Source: {upload2.source_type}")
    print(f"Filename: {upload2.filename}")
    print(f"\nText preview: {submission_text[:150]}...")

    print("\n🤖 Classifying document...")
    result2 = await classify_upload(upload2)

    print("\n" + "-" * 80)
    print("CLASSIFICATION RESULT")
    print("-" * 80)
    print(f"Document Type: {result2.document_type}")
    print(f"Confidence: {result2.confidence:.2f}")
    print(f"Reasoning: {result2.reasoning}")

    # Test 3: Other (thank you note)
    print("\n\n" + "=" * 80)
    print("TEST 3: OTHER (THANK YOU NOTE)")
    print("=" * 80)

    other_text = """
Dear Minister,

Thank you so much for attending our launch event last week. Your keynote speech
was inspiring and the feedback from attendees has been overwhelmingly positive.

Several people mentioned your insights on AI governance as particularly valuable.
We've had multiple requests for copies of your remarks.

We hope to have the opportunity to work with you again in the future.

Warm regards,
Emma Thompson
Director of Events
Tech Innovation UK
"""

    upload3 = ProcessedUpload(
        upload_id="TEST-003",
        text=other_text,
        source_type="email",
        subject="Thank you for your participation",
    )

    print(f"\nUpload ID: {upload3.upload_id}")
    print(f"Source: {upload3.source_type}")
    print(f"Subject: {upload3.subject}")
    print(f"\nText preview: {other_text[:150]}...")

    print("\n🤖 Classifying document...")
    result3 = await classify_upload(upload3)

    print("\n" + "-" * 80)
    print("CLASSIFICATION RESULT")
    print("-" * 80)
    print(f"Document Type: {result3.document_type}")
    print(f"Confidence: {result3.confidence:.2f}")
    print(f"Reasoning: {result3.reasoning}")

    # Test 4: Ambiguous (could be interpreted multiple ways)
    print("\n\n" + "=" * 80)
    print("TEST 4: AMBIGUOUS DOCUMENT")
    print("=" * 80)

    ambiguous_text = """
Minister,

The quarterly stakeholder forum is scheduled for 20 March 2026 at 10:00 AM.

We recommend that you chair the session and provide updates on the department's
AI strategy progress. Several key industry partners have requested your attendance.

The agenda includes reviewing the new partnership framework and discussing next
quarter's priorities.

Please confirm your availability.

David Chen
Head of Stakeholder Engagement
"""

    upload4 = ProcessedUpload(
        upload_id="TEST-004",
        text=ambiguous_text,
        source_type="email",
        subject="Quarterly Stakeholder Forum - March",
    )

    print(f"\nUpload ID: {upload4.upload_id}")
    print(f"Source: {upload4.source_type}")
    print(f"Subject: {upload4.subject}")
    print(f"\nText preview: {ambiguous_text[:150]}...")

    print("\n🤖 Classifying document...")
    result4 = await classify_upload(upload4)

    print("\n" + "-" * 80)
    print("CLASSIFICATION RESULT")
    print("-" * 80)
    print(f"Document Type: {result4.document_type}")
    print(f"Confidence: {result4.confidence:.2f}")
    print(f"Reasoning: {result4.reasoning}")

    # Summary
    print("\n\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"\nTest 1 (Invitation):     {result1.document_type} (confidence: {result1.confidence:.2f})")
    print(f"Test 2 (Submission):     {result2.document_type} (confidence: {result2.confidence:.2f})")
    print(f"Test 3 (Other):          {result3.document_type} (confidence: {result3.confidence:.2f})")
    print(f"Test 4 (Ambiguous):      {result4.document_type} (confidence: {result4.confidence:.2f})")

    print("\n" + "=" * 80)
    print("ALL TESTS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
