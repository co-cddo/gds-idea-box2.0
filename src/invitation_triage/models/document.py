import hashlib
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class RawDocument(BaseModel):
    """Raw Document type file before PII extraction."""

    document_id: str = Field(
        description="Unique identifier generated from content hash"
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
        """Generate a stable 16-character ID from document content."""
        content = f"{filename}{text}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


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
        """Extract PII and create SafeDocument."""
        # Reuse SafeEmail PII extraction methods
        from invitation_triage.models.email import SafeEmail

        # Extract PII and links (using empty subject since files don't have one)
        pii = SafeEmail._extract_pii("", raw_document.raw_text)
        links = SafeEmail._extract_links("", raw_document.raw_text)

        # Redact PII, then links
        safe_text = SafeEmail._redact_pii(raw_document.raw_text, pii)
        safe_text = SafeEmail._redact_links(safe_text, links)

        return cls(
            document_id=raw_document.document_id,
            filename=raw_document.filename,
            source_type=raw_document.source_type,
            safe_text=safe_text,
            document_timestamp=raw_document.document_timestamp,
            pii_extracted=pii,
            links_extracted=links,
            file_size=raw_document.file_size,
            metadata=raw_document.metadata,
        )

    def restore_pii(self, text: str) -> str:
        """Restore PII to redacted text (for authorized use)."""
        restored = text

        for i, email in enumerate(self.pii_extracted["emails"]):
            restored = restored.replace(f"[EMAIL_{i}]", email)

        for i, phone in enumerate(self.pii_extracted["phone_numbers"]):
            restored = restored.replace(f"[PHONE_{i}]", phone)

        return restored

    def restore_links(self, text: str) -> str:
        """Restore links to redacted text."""
        restored = text
        for link in self.links_extracted:
            restored = restored.replace(link["placeholder"], link["url"])
        return restored


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
