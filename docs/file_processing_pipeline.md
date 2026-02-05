# File Processing Pipeline

## Overview

The file processing pipeline converts uploaded files (PDF, DOCX, TXT) into `SafeUpload` objects ready for classification, following the same PII redaction pattern as the email pipeline.

## Architecture

```
File Upload (PDF/DOCX/TXT)
    ↓
extract_text_from_file()  # Text extraction
    ↓
RawUpload (upload_id, filename, source_type, raw_text, metadata)
    ↓
SafeUpload.from_raw_upload()  # PII extraction & redaction
    ↓
classify_upload()  # Ready for classification
```

## New Models

### RawUpload

Raw uploaded file before PII extraction (in `models/upload.py`):

```python
RawUpload(
    upload_id: str,          # Generated from content hash
    filename: str,
    source_type: "pdf" | "docx" | "txt",
    raw_text: str,           # Extracted text content
    upload_timestamp: datetime,
    file_size: int | None,
    metadata: dict           # page_count, etc.
)
```

### SafeUpload

Upload with PII extracted and redacted (in `models/upload.py`):

```python
SafeUpload(
    upload_id: str,
    filename: str,
    source_type: str,
    safe_text: str,                        # PII-redacted
    upload_timestamp: datetime,
    pii_extracted: dict[str, list[str]],   # emails, phone_numbers
    links_extracted: list[dict],            # URL placeholders
    file_size: int | None,
    metadata: dict
)
```

**Methods:**
- `from_raw_upload(raw_upload)` - Extract PII and create SafeUpload
- `restore_pii(text)` - Restore redacted PII (authorized use)
- `restore_links(text)` - Restore redacted URLs

## File Extraction Functions

Located in `src/invitation_triage/file_extraction.py`:

```python
extract_text_from_file(file_path, file_type=None) -> RawUpload
```

Main function that:
- Auto-detects file type from extension if not provided
- Extracts text using appropriate method
- Creates RawUpload with metadata

**Supported formats:**
- **PDF** - Uses `pypdf` library, extracts page count
- **DOCX** - Uses `python-docx`, extracts paragraph count
- **TXT** - Direct read, counts lines

## Usage Example

```python
from invitation_triage.file_extraction import extract_text_from_file
from invitation_triage.models.upload import SafeUpload
from invitation_triage.upload_classifier import classify_upload

# 1. Extract text from file
raw_upload = extract_text_from_file("document.pdf")

# 2. Redact PII
safe_upload = SafeUpload.from_raw_upload(raw_upload)

# 3. Classify
classification = await classify_upload(safe_upload)

# 4. Extract based on type
if classification.document_type == "submission":
    submission = await extract_submission(safe_upload.safe_text)
elif classification.document_type == "invitation":
    invitation = await extract_invitation_from_text(safe_upload.safe_text)
```

## Demo Script

Run the demo:

```bash
uv run python scripts/example_file_processing.py data/example_test.txt
```

The script demonstrates:
- Text extraction from file
- PII detection and redaction
- Metadata extraction
- SafeUpload ready for classification

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

1. **Classification** - SafeUpload → classify_upload()
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
