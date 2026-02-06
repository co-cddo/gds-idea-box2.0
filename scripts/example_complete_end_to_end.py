"""
Complete end-to-end test of the entire system.

Demonstrates the full workflow from document ingestion to action extraction:
1. Document arrives (email or file)
2. Extract/Classify/Triage
3. System generates draft response
4. Office responds (yes/yes_but/no + notes)
5. Redraft if needed
6. Extract actions
7. Save as JSON

Usage:
    uv run python scripts/example_complete_end_to_end.py
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

from invitation_triage.action_extraction import extract_actions
from invitation_triage.document_classifier import classify_document
from invitation_triage.invitation_extraction import extract_invitation
from invitation_triage.models import (
    MinisterPersona,
    NotInvitation,
    OfficeResponse,
    RawEmail,
    SafeEmail,
)
from invitation_triage.redraft import redraft_response
from invitation_triage.submission_extraction import extract_submission
from invitation_triage.triage import triage_invitation


async def main():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    print("=" * 80)
    print("COMPLETE END-TO-END SYSTEM TEST")
    print("=" * 80)
    print("\nThis demonstrates the full workflow from document to actions.\n")

    # ========================================================================
    # STEP 1: DOCUMENT ARRIVES
    # ========================================================================

    print("=" * 80)
    print("STEP 1: DOCUMENT ARRIVES")
    print("=" * 80)

    # Simulate an email invitation arriving
    raw_email = RawEmail(
        email_id="test_invite_001",
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
    )

    print(f"\n📧 Email Received: {raw_email.subject}")
    print(f"   From: Dr Sarah Chen")
    print(f"   Received: {raw_email.received_date}")

    # ========================================================================
    # STEP 2: PII REDACTION
    # ========================================================================

    print("\n" + "=" * 80)
    print("STEP 2: PII REDACTION")
    print("=" * 80)

    safe_email = SafeEmail.from_raw_email(raw_email)
    print(f"\n✓ PII Extracted:")
    print(f"  - Emails: {len(safe_email.pii_extracted['emails'])}")
    print(f"  - Phone numbers: {len(safe_email.pii_extracted['phone_numbers'])}")

    # ========================================================================
    # STEP 3: CONVERT TO DOCUMENT
    # ========================================================================

    print("\n" + "=" * 80)
    print("STEP 3: CONVERT TO UNIFIED DOCUMENT")
    print("=" * 80)

    safe_doc = safe_email.to_document()
    print(f"\n✓ SafeDocument created:")
    print(f"  - Document ID: {safe_doc.document_id}")
    print(f"  - Source: {safe_doc.source_type}")

    # ========================================================================
    # STEP 4: CLASSIFY DOCUMENT
    # ========================================================================

    print("\n" + "=" * 80)
    print("STEP 4: CLASSIFY DOCUMENT TYPE")
    print("=" * 80)

    classification = await classify_document(safe_doc)
    print(f"\n✓ Classification:")
    print(f"  - Type: {classification.document_type}")
    print(f"  - Confidence: {classification.confidence:.2f}")

    # ========================================================================
    # STEP 5: EXTRACT STRUCTURED DATA
    # ========================================================================

    print("\n" + "=" * 80)
    print("STEP 5: EXTRACT STRUCTURED DATA")
    print("=" * 80)

    if classification.document_type == "invitation":
        extracted = await extract_invitation(safe_doc)
        if isinstance(extracted, NotInvitation):
            print(f"\n✗ Not an invitation: {extracted.reason}")
            return

        print(f"\n✓ Invitation Extracted:")
        print(f"  - Event: {extracted.event_type}")
        print(f"  - Host: {extracted.host_org}")
        print(f"  - Location: {extracted.location}")
        print(f"  - Time: {', '.join(extracted.proposed_times)}")

    elif classification.document_type == "submission":
        extracted = await extract_submission(safe_doc)
        print(f"\n✓ Submission Extracted:")
        print(f"  - Policy Area: {extracted.policy_area}")
        print(f"  - Official Recommendation: {extracted.official_recommendation}")
    else:
        print(f"\n✗ Document type '{classification.document_type}' not supported")
        return

    # ========================================================================
    # STEP 6: TRIAGE (for invitations only)
    # ========================================================================

    if classification.document_type == "invitation":
        print("\n" + "=" * 80)
        print("STEP 6: TRIAGE AGAINST MINISTER'S PRIORITIES")
        print("=" * 80)

        persona = MinisterPersona.from_json_file("data/example_science_minister.json")
        print(f"\n👤 Minister: {persona.name}")

        triaged = await triage_invitation(extracted, persona)
        source = triaged

        print(f"\n✓ Triage Decision:")
        print(f"  - Recommendation: {triaged.decision}")
        print(f"  - Priority: {triaged.priority}")
        print(f"  - Reasoning: {triaged.reason[:100]}...")

        original_draft = triaged.draft_response
    else:
        source = extracted
        original_draft = extracted.draft_response

    print("\n✉️  System Generated Draft:")
    print("-" * 80)
    print(original_draft[:200] + "...")
    print("-" * 80)

    # ========================================================================
    # STEP 7: OFFICE RESPONDS
    # ========================================================================

    print("\n" + "=" * 80)
    print("STEP 7: PRIVATE OFFICE RESPONDS")
    print("=" * 80)

    # Simulate office response - "yes_but" with modification
    office_response = OfficeResponse(
        document_id=safe_doc.document_id,
        document_type=classification.document_type,
        decision="yes_but",
        notes="Can only attend from 7pm onwards due to Cabinet committee",
    )

    print(f"\n📝 Office Response:")
    print(f"  - Decision: {office_response.decision}")
    print(f"  - Notes: {office_response.notes}")

    # ========================================================================
    # STEP 8: REDRAFT IF NEEDED
    # ========================================================================

    print("\n" + "=" * 80)
    print("STEP 8: REDRAFT RESPONSE")
    print("=" * 80)

    if office_response.decision in ["yes_but", "no"]:
        print("\n🤖 Redrafting based on office notes...")
        final_draft = await redraft_response(
            original_draft=original_draft,
            office_notes=office_response.notes,
            source=source,
            document_type=classification.document_type,
        )
        print("\n✓ Draft redrafted to incorporate modifications")
    else:
        final_draft = original_draft
        print("\n✓ Using original draft (no modifications needed)")

    print("\n✉️  Final Draft:")
    print("-" * 80)
    print(final_draft)
    print("-" * 80)

    # ========================================================================
    # STEP 9: EXTRACT ACTIONS
    # ========================================================================

    print("\n" + "=" * 80)
    print("STEP 9: EXTRACT ACTIONABLE ITEMS")
    print("=" * 80)

    print("\n🤖 Extracting actions from decision...")
    result = await extract_actions(
        document=safe_doc,
        classification=classification,
        source=source,
        office_response=office_response,
        final_draft=final_draft,
    )

    print(f"\n✓ Actions Extracted:")
    print(f"  - Total: {len(result.actions)} action(s)")
    print(f"  - Summary: {result.summary}")

    print("\n📋 Action Details:")
    for i, action in enumerate(result.actions, 1):
        print(f"\n  {i}. {action.description}")
        print(f"     Type: {action.action_type}")
        print(f"     Urgency: {action.urgency}")
        if action.deadline:
            print(f"     Deadline: {action.deadline}")
        if action.owner:
            print(f"     Owner: {action.owner}")
        if action.draft_content:
            print(f"     Draft: {len(action.draft_content)} chars")

    # ========================================================================
    # STEP 10: SAVE AS JSON
    # ========================================================================

    print("\n" + "=" * 80)
    print("STEP 10: SAVE RESULT AS JSON")
    print("=" * 80)

    # Convert to JSON
    result_dict = result.model_dump(mode="json")

    # Save to file
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / f"actions_{safe_doc.document_id}.json"
    with open(output_file, "w") as f:
        json.dump(result_dict, f, indent=2)

    print(f"\n✓ Result saved to: {output_file}")
    print(f"  - File size: {output_file.stat().st_size:,} bytes")

    print("\n📄 JSON Preview:")
    print(json.dumps(result_dict, indent=2)[:500] + "...")

    # ========================================================================
    # COMPLETE
    # ========================================================================

    print("\n" + "=" * 80)
    print("✨ COMPLETE END-TO-END TEST SUCCESSFUL!")
    print("=" * 80)

    print("\n📊 System Summary:")
    print(f"  - Document Type: {classification.document_type}")
    print(f"  - Office Decision: {office_response.decision}")
    print(f"  - Draft Modified: {result.final_draft.was_modified}")
    print(f"  - Actions Extracted: {len(result.actions)}")
    print(f"  - Saved to: {output_file}")

    print("\n✅ The complete system is working end-to-end!")


if __name__ == "__main__":
    asyncio.run(main())
