# File Processing Pipeline

## Overview

The file processing pipeline converts documented files (PDF, DOCX, TXT) into `SafeDocument` objects ready for classification, following the same PII redaction pattern as the email pipeline.

## Architecture

```
File document (PDF/DOCX/TXT)
    ↓
extract_text_from_file()  # Text extraction
    ↓
RawDocument (document_id, filename, source_type, raw_text, metadata)
    ↓
SafeDocument.from_raw_document()  # PII extraction & redaction
    ↓
classify_document()  # Ready for classification
```

## New Models

### RawDocument

Raw documented file before PII extraction (in `models/document.py`):

```python
RawDocument(
    document_id: str,          # Generated from content hash
    filename: str,
    source_type: "pdf" | "docx" | "txt",
    raw_text: str,           # Extracted text content
    document_timestamp: datetime,
    file_size: int | None,
    metadata: dict           # page_count, etc.
)
```

### SafeDocument

document with PII extracted and redacted (in `models/document.py`):

```python
SafeDocument(
    document_id: str,
    filename: str,
    source_type: str,
    safe_text: str,                        # PII-redacted
    document_timestamp: datetime,
    pii_extracted: dict[str, list[str]],   # emails, phone_numbers
    links_extracted: list[dict],            # URL placeholders
    file_size: int | None,
    metadata: dict
)
```

**Methods:**
- `from_raw_document(raw_document)` - Extract PII and create SafeDocument
- `restore_pii(text)` - Restore redacted PII (authorized use)
- `restore_links(text)` - Restore redacted URLs

## File Extraction Functions

Located in `src/box2.triage/file_extraction.py`:

```python
extract_text_from_file(file_path, file_type=None) -> RawDocument
```

Main function that:
- Auto-detects file type from extension if not provided
- Extracts text using appropriate method
- Creates RawDocument with metadata

**Supported formats:**
- **PDF** - Uses `pypdf` library, extracts page count
- **DOCX** - Uses `python-docx`, extracts paragraph count
- **TXT** - Direct read, counts lines

## Usage Example

```python
from box2.triage.file_extraction import extract_text_from_file
from box2.triage.models.document import SafeDocument
from box2.triage.document_classifier import classify_document

# 1. Extract text from file
raw_document = extract_text_from_file("document.pdf")

# 2. Redact PII
safe_document = SafeDocument.from_raw_document(raw_document)

# 3. Classify
classification = await classify_document(safe_document)

# 4. Extract based on type
if classification.document_type == "submission":
    submission = await extract_submission(safe_document.safe_text)
elif classification.document_type == "invitation":
    invitation = await extract_invitation_from_text(safe_document.safe_text)
```

## Demo Script

Run the demo:

```bash
uv run python examples/example_file_processing.py examples/data/example_test.txt
```

The script demonstrates:
- Text extraction from file
- PII detection and redaction
- Metadata extraction
- SafeDocument ready for classification

## Dependencies

Added to `pyproject.toml`:
- `pypdf>=5.3.0` - PDF text extraction
- `python-docx>=1.1.2` - Word document extraction

Install with:
```bash
uv sync
```

## PII Protection

The pipeline reuses the `SafeEmail` PII extraction methods:
- Email addresses → `[EMAIL_0]`, `[EMAIL_1]`, etc.
- Phone numbers → `[PHONE_0]`, `[PHONE_1]`, etc.
- URLs → `[LINK_0: domain.com]` (domain visible)

PII is stored separately in `pii_extracted` and `links_extracted` dictionaries.

## Testing

Run tests:
```bash
uv run pytest -v
```

Check code style:
```bash
uv run ruff check .
```

## Integration Points

The file processing pipeline integrates with existing components:

1. **Classification** - SafeDocument → classify_document()
2. **Extraction** - Based on classification type
3. **Calendar** - For invitation triage
4. **Decision** - For submission processing

## Future Enhancements

Potential improvements:
- Support for more file formats (RTF, HTML, etc.)
- OCR for scanned documents
- Better name extraction (NER)
- File size limits and validation
- Virus scanning integration
