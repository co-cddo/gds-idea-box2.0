"""
Complete end-to-end test of email processing pipeline.

This script demonstrates the full pipeline for email invitations:
1. Raw email → SafeEmail (PII redaction)
2. SafeEmail → SafeDocument (unified document format)
3. SafeDocument → Invitation extraction (LLM)
4. Invitation → Triaged decision with calendar checking (LLM)

Usage:
    uv run python examples/example_email_end_to_end.py
"""

import asyncio
import logging
from datetime import datetime

from box2.triage.invitation_extraction import extract_invitation
from box2.triage.models import (
    MinisterPersona,
    NotInvitation,
    RawEmail,
    SafeEmail,
)
from box2.triage.triage import triage_invitation


async def main():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Sample emails to process
    emails = [
        RawEmail(
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
+441234567890
""",
            received_date=datetime(2026, 1, 20, 9, 15),
            has_attachments=False,
        ),
        RawEmail(
            email_id="test_002",
            subject="Drinks next week?",
            body="""Hi,

Fancy catching up over drinks at Simmons Bar? We haven't seen you in ages!

Could do Friday evening or next Tuesday after 6pm. Let us know what works.

Matt and David
""",
            received_date=datetime(2026, 1, 21, 14, 30),
            has_attachments=False,
        ),
        RawEmail(
            email_id="test_003",
            subject="Thank you for your speech",
            body="""Dear Minister,

Thank you so much for your inspiring speech at last week's conference on quantum computing. Your vision for UK leadership in quantum technologies really resonated with our members.

We've published a summary on our website and received excellent feedback.

Best regards,
Jane Smith
Tech UK
""",
            received_date=datetime(2026, 1, 22, 10, 0),
            has_attachments=False,
        ),
    ]

    # Load minister persona
    print("=" * 80)
    print("COMPLETE END-TO-END INVITATION TRIAGE TEST")
    print("=" * 80)

    persona = MinisterPersona.from_json_file("src/box2/triage/data/example_science_minister.json")
    print(f"\n👤 MINISTER: {persona.name}")
    print(f"   Role: {persona.role}")
    print(f"   Top Priority: {persona.priorities[0]}")

    # Process each email
    for i, raw_email in enumerate(emails, 1):
        print("\n" + "=" * 80)
        print(f"EMAIL {i} OF {len(emails)}")
        print("=" * 80)
        print(f"\n📧 SUBJECT: {raw_email.subject}")
        print(f"   Received: {raw_email.received_date}")

        # ====================================================================
        # PHASE 1: EXTRACTION
        # ====================================================================

        # Step 1a: Convert to SafeEmail (redact PII)
        print("\n🔒 Step 1: Redacting PII...")
        safe_email = SafeEmail.from_raw_email(raw_email)
        print(f"   - Emails extracted: {len(safe_email.pii_extracted['emails'])}")
        print(f"   - Phone numbers extracted: {len(safe_email.pii_extracted['phone_numbers'])}")
        print(f"   - Links extracted: {len(safe_email.links_extracted)}")

        # Step 1b: Convert to SafeDocument
        print("\n📄 Step 2: Converting to SafeDocument...")
        safe_doc = safe_email.to_document()
        print(f"   - Document ID: {safe_doc.document_id[:16]}...")
        print(f"   - Source: {safe_doc.source_type}")

        # Step 1c: Extract invitation details
        print("\n🤖 Step 3: Extracting invitation details with LLM...")
        result = await extract_invitation(safe_doc)

        # Check if it's an invitation
        if isinstance(result, NotInvitation):
            print("\n❌ NOT AN INVITATION")
            print(f"   Reason: {result.reason}")
            print("\n   → Skipping triage (no action needed)")
            continue

        # ====================================================================
        # PHASE 2: TRIAGE
        # ====================================================================

        print("\n✅ INVITATION DETECTED")
        invitation = result
        print(f"   Event Type: {invitation.event_type}")
        print(f"   Host: {invitation.host_org}")
        print(f"   Topics: {', '.join(invitation.topics) if invitation.topics else 'None'}")
        print(f"   Time: {', '.join(invitation.proposed_times)}")
        print(f"   Location: {invitation.location}")

        # Step 2: Triage with calendar checking
        print("\n🤖 Step 4: Triaging (checking calendar & making recommendation)...")
        triaged = await triage_invitation(invitation, persona)

        # ====================================================================
        # RESULTS
        # ====================================================================

        print("\n" + "-" * 80)
        print("📋 TRIAGE RESULTS")
        print("-" * 80)

        print(f"\n🎯 DECISION: {triaged.decision.upper()}")
        print(f"   Priority: {triaged.priority.upper()}")

        print("\n💭 REASONING:")
        print(f"   {triaged.reason}")

        if triaged.affected_events:
            print("\n📅 CALENDAR CONFLICTS:")
            for event in triaged.affected_events:
                print(f"   - {event}")
        else:
            print("\n📅 No calendar conflicts found")

        print("\n✉️  DRAFT RESPONSE:")
        print("-" * 80)
        print(triaged.draft_response)
        print("-" * 80)

    print("\n" + "=" * 80)
    print("✨ All emails processed!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
