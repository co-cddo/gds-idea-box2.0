"""
Complete end-to-end test of file document processing pipeline.

This script demonstrates the full pipeline for file uploads:
1. File (PDF/DOCX/TXT) → RawDocument (text extraction)
2. RawDocument → SafeDocument (PII redaction)
3. SafeDocument → DocumentClassification (LLM classification)
4. Branching based on document type:
   - invitation → Invitation extraction → Triage decision
   - submission → Submission extraction
   - other → Not yet supported

Usage:
    uv run python examples/example_file_end_to_end.py <file_path>

Example:
    uv run python examples/example_file_end_to_end.py data/example_invitation.pdf
    uv run python examples/example_file_end_to_end.py data/example_submission.docx
"""

import asyncio
import logging
import sys

from box2.triage.document_classifier import classify_document
from box2.triage.file_parser import extract_text_from_file
from box2.triage.invitation_extraction import extract_invitation
from box2.triage.models import (
    MinisterPersona,
    NotInvitation,
    NotSubmission,
    SafeDocument,
)
from box2.triage.submission_extraction import extract_submission
from box2.triage.triage import triage_invitation


async def main():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Check for file path argument
    if len(sys.argv) < 2:
        print("Usage: uv run python examples/example_file_end_to_end.py <file_path>")
        print("\nExample:")
        print("  uv run python examples/example_file_end_to_end.py data/invitation.pdf")
        sys.exit(1)

    file_path = sys.argv[1]

    print("=" * 80)
    print("COMPLETE FILE DOCUMENT PROCESSING PIPELINE")
    print("=" * 80)

    # ====================================================================
    # PHASE 0: FILE PARSING
    # ====================================================================

    print(f"\n📄 PROCESSING FILE: {file_path}")

    # Step 1: Extract text from file
    print("\n🔍 Step 1: Extracting text from file...")
    try:
        raw_document = extract_text_from_file(file_path)
    except FileNotFoundError:
        print(f"   ❌ Error: File not found: {file_path}")
        sys.exit(1)
    except Exception as e:
        print(f"   ❌ Error extracting text: {e}")
        sys.exit(1)

    print(f"   ✓ Extracted {len(raw_document.raw_text)} characters")
    print(f"   ✓ File type: {raw_document.source_type}")
    print(f"   ✓ Document ID: {raw_document.document_id[:16]}...")
    print(f"   ✓ File size: {raw_document.file_size:,} bytes")

    # Step 2: Extract PII and create SafeDocument
    print("\n🔒 Step 2: Redacting PII...")
    safe_doc = SafeDocument.from_raw_document(raw_document)
    print(f"   ✓ Emails extracted: {len(safe_doc.pii_extracted['emails'])}")
    print(
        f"   ✓ Phone numbers extracted: {len(safe_doc.pii_extracted['phone_numbers'])}"
    )
    print(f"   ✓ Links extracted: {len(safe_doc.links_extracted)}")

    # ====================================================================
    # PHASE 1: CLASSIFICATION
    # ====================================================================

    print("\n🤖 Step 3: Classifying document type...")
    classification = await classify_document(safe_doc)
    print(f"   ✓ Type: {classification.document_type}")
    print(f"   ✓ Confidence: {classification.confidence:.2f}")
    print(f"   ✓ Reasoning: {classification.reasoning}")

    # ====================================================================
    # PHASE 2: EXTRACTION (BRANCHING BASED ON TYPE)
    # ====================================================================

    if classification.document_type == "invitation":
        print("\n" + "=" * 80)
        print("INVITATION DETECTED")
        print("=" * 80)

        # Extract invitation
        print("\n🤖 Step 4: Extracting invitation details...")
        result = await extract_invitation(safe_doc)

        if isinstance(result, NotInvitation):
            print("\n❌ NOT AN INVITATION (classifier was wrong)")
            print(f"   Reason: {result.reason}")
            print("\n   → No further processing")
        else:
            invitation = result
            print("\n✅ INVITATION EXTRACTED")
            print(f"   Event Type: {invitation.event_type}")
            print(f"   Host: {invitation.host_org}")
            print(
                f"   Topics: {', '.join(invitation.topics) if invitation.topics else 'None'}"
            )
            print(f"   Time: {', '.join(invitation.proposed_times)}")
            print(f"   Location: {invitation.location}")

            # ================================================================
            # PHASE 3: TRIAGE (IF PERSONA AVAILABLE)
            # ================================================================

            # Try to load persona
            try:
                persona = MinisterPersona.from_json_file(
                    "src/box2/triage/data/example_science_minister.json"
                )
                print(f"\n👤 MINISTER: {persona.name}")
                print(f"   Role: {persona.role}")

                print("\n🤖 Step 5: Triaging invitation...")
                triaged = await triage_invitation(invitation, persona)

                print("\n" + "-" * 80)
                print("📋 TRIAGE RESULTS")
                print("-" * 80)

                print(f"\n🎯 DECISION: {triaged.decision.upper()}")
                print(f"   Priority: {triaged.priority.upper()}")

                print(f"\n💭 REASONING:")
                print(f"   {triaged.reason}")

                if triaged.affected_events:
                    print(f"\n📅 CALENDAR CONFLICTS:")
                    for event in triaged.affected_events:
                        print(f"   - {event}")
                else:
                    print("\n📅 No calendar conflicts found")

                print(f"\n✉️  DRAFT RESPONSE:")
                print("-" * 80)
                print(triaged.draft_response)
                print("-" * 80)

            except FileNotFoundError:
                print("\n⚠️  No persona file found (src/box2/triage/data/example_science_minister.json)")
                print("   → Skipping triage step")

    elif classification.document_type == "submission":
        print("\n" + "=" * 80)
        print("SUBMISSION DETECTED")
        print("=" * 80)

        # Extract submission
        print("\n🤖 Step 4: Extracting submission details...")
        result = await extract_submission(safe_doc)

        if isinstance(result, NotSubmission):
            print("\n❌ NOT A SUBMISSION (classifier was wrong)")
            print(f"   Reason: {result.reason}")
            if result.suggested_category:
                print(f"   Suggested Category: {result.suggested_category}")
            print("\n   → No further processing")
        else:
            submission = result
            print("\n✅ SUBMISSION EXTRACTED")
            print(f"   Document ID: {submission.document_id}")
            print(f"   Policy Area: {submission.policy_area}")
            print(f"   Responsible Official: {submission.responsible_deputy_director}")
            print(f"   Urgency: {submission.urgency_assessment}")

            if submission.decision_deadline:
                print(f"   Decision Deadline: {submission.decision_deadline}")

            print(f"\n📝 OFFICIAL RECOMMENDATION:")
            print(f"   {submission.official_recommendation}")

            if submission.required_decisions:
                print(f"\n✅ REQUIRED DECISIONS:")
                for decision in submission.required_decisions:
                    print(f"   - {decision}")

            if submission.key_dates:
                print(f"\n📅 KEY DATES:")
                for date in submission.key_dates:
                    print(f"   - {date}")

            if submission.related_items:
                print(f"\n🔗 RELATED ITEMS:")
                for item in submission.related_items:
                    print(f"   - {item}")

            print(f"\n📄 SUMMARY:")
            print(f"   {submission.summary}")

            print(
                "\n💡 NOTE: Submissions contain official recommendations"
            )
            print("   → Reply is generated after minister responds (template-based, no LLM)")

    elif classification.document_type == "other":
        print("\n" + "=" * 80)
        print("DOCUMENT TYPE: OTHER")
        print("=" * 80)
        print("\nℹ️  This document doesn't match invitation or submission patterns.")
        print("   Document type 'other' is not yet supported for extraction.")
        print("\n   → No further processing")

    print("\n" + "=" * 80)
    print("✨ Processing complete!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
