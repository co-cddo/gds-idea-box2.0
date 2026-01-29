"""
End-to-end test of invitation extraction.

Usage:
    uv run python example_extraction.py
"""

import asyncio
from datetime import datetime

from invitation_triage.extraction import extract_invitation
from invitation_triage.models import NotInvitation, RawEmail, SafeEmail


async def main():
    # Create a sample email
    raw_email = RawEmail(
        email_id="test_001",
        subject="Invitation: AI Safety Summit Reception",
        body="""Dear Minister,

We would be delighted if you could join us for a reception celebrating the launch of the UK AI Safety Institute's latest research findings. This will be an excellent opportunity to meet with leading AI researchers and industry partners.

Date: 15th February 2026, 6:00 PM - 8:00 PM
Location: The Royal Society, London
RSVP by: 5th February 2026

The event will showcase breakthrough work on AI model evaluation and safety benchmarking. Several international delegations will be in attendance.

Best regards,
Dr Sarah Chen
Director, UK AI Safety Institute
sarah.chen@aisi.gov.uk
""",
        received_date=datetime(2026, 1, 20, 9, 15),
        has_attachments=False,
    )

    print("=" * 80)
    print("EXTRACTION TEST")
    print("=" * 80)
    print(f"\nEmail Subject: {raw_email.subject}")
    print(f"Received: {raw_email.received_date}")

    # Convert to SafeEmail (redact PII)
    print("\n📧 Converting to SafeEmail (redacting PII)...")
    safe_email = SafeEmail.from_raw_email(raw_email)
    print(f"   - Emails extracted: {len(safe_email.pii_extracted['emails'])}")
    print(f"   - Links extracted: {len(safe_email.links_extracted)}")

    # Extract invitation
    print("\n🤖 Extracting invitation details with LLM...")
    result = await extract_invitation(safe_email)

    # Display results
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)

    if isinstance(result, NotInvitation):
        print("\n❌ NOT AN INVITATION")
        print(f"Reason: {result.reason}")
    else:
        print("\n✅ INVITATION DETECTED")
        print(f"\nEvent Type: {result.event_type}")
        print(f"Host: {result.host_org}")
        print(f"Location: {result.location}")
        print(f"Topics: {', '.join(result.topics)}")
        print(f"Time Flexible: {result.is_time_flexible}")
        print("\nProposed Times:")
        for time in result.proposed_times:
            print(f"   - {time}")
        print(f"\nSummary: {result.event_summary}")
        if result.deadline_to_respond:
            print(f"Deadline: {result.deadline_to_respond}")
        if result.overall_confidence:
            print(f"Confidence: {result.overall_confidence:.2f}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
