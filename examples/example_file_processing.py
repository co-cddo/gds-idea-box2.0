"""
Example script demonstrating file document processing pipeline.

Shows the complete flow:
1. Extract text from file (PDF/DOCX/TXT)
2. Create RawDocument
3. Extract PII to create SafeDocument
4. Ready for classification

Usage:
    uv run python scripts/example_file_processing.py <file_path>

Example:
    uv run python scripts/example_file_processing.py data/example_submission.pdf
"""

import sys

from box2.triage.file_parser import extract_text_from_file
from box2.triage.models.document import SafeDocument


def main():
    """Demonstrate file processing pipeline."""

    # Check for file path argument
    if len(sys.argv) < 2:
        print("Usage: uv run python scripts/example_file_processing.py <file_path>")
        print("\nExample:")
        print("  uv run python scripts/example_file_processing.py data/example.pdf")
        sys.exit(1)

    file_path = sys.argv[1]

    print("=" * 80)
    print("FILE document PROCESSING PIPELINE")
    print("=" * 80)

    # Step 1: Extract text from file
    print(f"\n1. Extracting text from: {file_path}")
    try:
        raw_document = extract_text_from_file(file_path)
    except Exception as e:
        print(f"Error extracting text: {e}")
        sys.exit(1)

    print(f"   ✓ Extracted {len(raw_document.raw_text)} characters")
    print(f"   ✓ File type: {raw_document.source_type}")
    print(f"   ✓ document ID: {raw_document.document_id}")
    print(f"   ✓ File size: {raw_document.file_size:,} bytes")
    print(f"   ✓ Metadata: {raw_document.metadata}")

    # Show preview of extracted text
    preview_length = 500
    text_preview = raw_document.raw_text[:preview_length]
    if len(raw_document.raw_text) > preview_length:
        text_preview += "..."

    print("\n   Text preview:")
    print("   " + "-" * 70)
    for line in text_preview.split("\n")[:10]:
        print(f"   {line}")
    if len(raw_document.raw_text.split("\n")) > 10:
        print("   ...")
    print("   " + "-" * 70)

    # Step 2: Extract PII and create SafeDocument
    print("\n2. Extracting PII and creating SafeDocument...")
    safe_document = SafeDocument.from_raw_document(raw_document)

    print(f"   ✓ Extracted {len(safe_document.pii_extracted['emails'])} email(s)")
    phone_count = len(safe_document.pii_extracted["phone_numbers"])
    print(f"   ✓ Extracted {phone_count} phone number(s)")
    print(f"   ✓ Extracted {len(safe_document.links_extracted)} link(s)")

    # Show what was extracted
    if safe_document.pii_extracted["emails"]:
        print("\n   Emails found:")
        for i, email in enumerate(safe_document.pii_extracted["emails"]):
            print(f"     [EMAIL_{i}] -> {email}")

    if safe_document.pii_extracted["phone_numbers"]:
        print("\n   Phone numbers found:")
        for i, phone in enumerate(safe_document.pii_extracted["phone_numbers"]):
            print(f"     [PHONE_{i}] -> {phone}")

    if safe_document.links_extracted:
        print("\n   Links found:")
        for link in safe_document.links_extracted:
            print(f"     {link['placeholder']} -> {link['url'][:60]}...")

    # Show redacted text preview
    safe_preview_length = 500
    safe_text_preview = safe_document.safe_text[:safe_preview_length]
    if len(safe_document.safe_text) > safe_preview_length:
        safe_text_preview += "..."

    print("\n   Redacted text preview:")
    print("   " + "-" * 70)
    for line in safe_text_preview.split("\n")[:10]:
        print(f"   {line}")
    if len(safe_document.safe_text.split("\n")) > 10:
        print("   ...")
    print("   " + "-" * 70)

    # Step 3: Ready for classification
    print("\n3. Ready for classification pipeline:")
    print("   → SafeDocument can now be passed to classify_document()")
    print("   → classification = await classify_document(safe_document)")
    print("   → Based on classification, route to:")
    print("      - extract_invitation() for 'invitation' type")
    print("      - extract_submission() for 'submission' type")
    print("      - Handle as 'other' type")

    print("\n" + "=" * 80)
    print("PIPELINE COMPLETE")
    print("=" * 80)
    print("\nNext steps:")
    print("  1. Pass SafeDocument to classify_document()")
    print("  2. Extract structured data based on classification")
    print("  3. PII can be restored using safe_document.restore_pii() when authorized")


if __name__ == "__main__":
    main()
