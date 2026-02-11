import hashlib
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from invitation_triage.pii_redaction import PIIRedactor


def generate_document_id(content: str, prefix: str = "doc") -> str:
    """Generate a deterministic document ID from content hash.

    Creates a stable, prefixed identifier by hashing the input content.
    The same content always produces the same ID, enabling deduplication.

    Args:
        content: String content to hash (e.g. email subject+body, file text)
        prefix: Type prefix indicating document origin
            ('email' for emails, 'file' for uploaded files)

    Returns:
        Prefixed 16-char hex hash, e.g. 'email_a1b2c3d4e5f6g7h8'
    """
    hash_str = hashlib.sha256(content.encode()).hexdigest()[:16]
    return f"{prefix}_{hash_str}"


class RawDocument(BaseModel):
    """Raw Document type file before PII extraction."""

    document_id: str = Field(
        description="Unique identifier generated from content hash (file_{hash})"
    )
    filename: str = Field(description="Original filename")
    source_type: Literal["pdf", "docx", "txt"] = Field(description="File type")
    raw_text: str = Field(description="Extracted text content from file")
    document_timestamp: datetime = Field(
        default_factory=datetime.now, description="When this file was processed"
    )
    file_size: int | None = Field(default=None, description="File size in bytes")
    metadata: dict = Field(
        default_factory=dict, description="Additional metadata (page_count, etc.)"
    )

    @classmethod
    def _generate_document_id(cls, text: str, filename: str) -> str:
        """Generate a stable document ID from file content."""
        return generate_document_id(f"{filename}{text}", prefix="file")


class SafeDocument(BaseModel):
    """Document with PII extracted and redacted."""

    document_id: str
    filename: str
    source_type: str
    safe_text: str = Field(description="PII-redacted text content")
    document_timestamp: datetime
    pii_extracted: dict[str, list[str]] = Field(
        description="Extracted PII (emails, phone numbers)"
    )
    links_extracted: list[dict[str, str]] = Field(
        description="Extracted links with placeholders"
    )
    file_size: int | None = None
    metadata: dict = Field(default_factory=dict)

    @classmethod
    def from_raw_document(cls, raw_document: "RawDocument") -> "SafeDocument":
        """Extract PII and create SafeDocument using PIIRedactor."""
        # Create PIIRedactor instance for this document
        redactor = PIIRedactor()

        # Process text through redactor
        safe_text = redactor.process(raw_document.raw_text)

        return cls(
            document_id=raw_document.document_id,
            filename=raw_document.filename,
            source_type=raw_document.source_type,
            safe_text=safe_text,
            document_timestamp=raw_document.document_timestamp,
            pii_extracted=redactor.pii,  # Access accumulated PII
            links_extracted=redactor.links,  # Access accumulated links
            file_size=raw_document.file_size,
            metadata=raw_document.metadata,
        )

    def restore_pii(self, text: str) -> str:
        """Restore PII to redacted text (for authorized use)."""
        return PIIRedactor.restore_pii(text, self.pii_extracted)

    def restore_links(self, text: str) -> str:
        """Restore links to redacted text."""
        return PIIRedactor.restore_links(text, self.links_extracted)


class DocumentClassification(BaseModel):
    """
    Result of classifying an document.

    Determines what type of ministerial document this is for routing to
    appropriate extraction and processing pipelines.
    """

    document_id: str = Field(
        description="Links back to the SafeDocument that was classified"
    )

    document_type: Literal["invitation", "submission", "other"] = Field(
        description="Classified document type. "
        "'invitation' = event attendance request, "
        "'submission' = ministerial submission requesting decision, "
        "'other' = unrecognized or general correspondence"
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score (0.0-1.0) in this classification. "
        "0.9+ = very confident, 0.5-0.7 = ambiguous, <0.5 = low confidence",
    )

    reasoning: str = Field(
        min_length=10,
        description="Brief explanation of why this classification was chosen",
    )
