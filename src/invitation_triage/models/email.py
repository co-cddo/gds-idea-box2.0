import hashlib
from datetime import datetime
from typing import Any

import pandas as pd
from dateutil import parser
from pydantic import BaseModel, Field, model_validator

from invitation_triage.models.document import (
    RawDocument,
    SafeDocument,
    generate_document_id,
)
from invitation_triage.pii_redaction import PIIRedactor


class RawEmail(BaseModel):
    """Raw email as ingested from CSV or other source."""

    email_id: str = Field(
        description="Source system email identifier "
        "(e.g., Outlook message ID, Gmail ID, or auto-generated hash)"
    )
    document_id: str = Field(
        default="",
        description="App-wide tracking ID (email_{hash}). "
        "Auto-generated from content if not provided.",
    )
    subject: str
    body: str
    received_date: datetime
    has_attachments: bool = False
    attachments: list[RawDocument] = Field(
        default_factory=list,
        description="Email attachments as RawDocuments "
        "(empty for current MVP test data)",
    )

    @model_validator(mode="after")
    def set_document_id(self) -> "RawEmail":
        """Generate document_id from content hash if not explicitly provided."""
        if not self.document_id:
            self.document_id = generate_document_id(
                f"{self.subject}{self.body}{self.received_date}",
                prefix="email",
            )
        return self

    @classmethod
    def _generate_id(
        cls, subject: str, body: str, received_date: str | datetime
    ) -> str:
        """Generate a stable 16-character ID from email content."""
        received_str = str(received_date)
        content = f"{subject}{body}{received_str}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    @classmethod
    def from_dataframe_row(cls, row: pd.Series) -> "RawEmail":
        """
        Create RawEmail from a pandas DataFrame row.

        Expected columns: Subject, Body, Received date and time, Has attachments
        """
        email_id = cls._generate_id(
            row["Subject"], row["Body"], row["Received date and time"]
        )

        return cls(
            email_id=email_id,
            subject=row["Subject"],
            body=row["Body"],
            received_date=parser.parse(row["Received date and time"]),
            has_attachments=str(row["Has attachments"]).lower() == "true",
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RawEmail":
        """
        Create RawEmail from a dictionary.

        Flexible constructor - handles various dict formats.
        """
        # If email_id not provided, generate from content
        if "email_id" not in data:
            data["email_id"] = cls._generate_id(
                data.get("subject", ""),
                data.get("body", ""),
                data.get("received_date", ""),
            )

        # Parse received_date if it's a string
        if isinstance(data.get("received_date"), str):
            data["received_date"] = parser.parse(data["received_date"])

        return cls(**data)

    @classmethod
    def from_outlook_api(cls, outlook_message: dict[str, Any]) -> "RawEmail":
        """
        Create RawEmail from Microsoft Outlook API response.

        Args:
            outlook_message: Message object from Outlook Graph API

        TODO: Implement Outlook API message parsing
        """
        raise NotImplementedError("Outlook API integration not yet implemented")

    @classmethod
    def from_gmail_api(cls, gmail_message: dict[str, Any]) -> "RawEmail":
        """
        Create RawEmail from Gmail API response.

        Args:
            gmail_message: Message object from Gmail API

        TODO: Implement Gmail API message parsing
        """
        raise NotImplementedError("Gmail API integration not yet implemented")


class SafeEmail(BaseModel):
    """Email with PII removed and stored separately for secure handling."""

    email_id: str = Field(
        description="Source system email identifier"
    )
    document_id: str = Field(
        description="App-wide tracking ID (email_{hash})"
    )
    subject: str  # PII-redacted
    body: str  # PII-redacted
    received_date: datetime
    has_attachments: bool = False
    attachments: list[SafeDocument] = Field(
        default_factory=list,
        description="Processed email attachments (empty for MVP test data)",
    )
    pii_extracted: dict[str, list[str]]
    links_extracted: list[dict[str, str]]

    @classmethod
    def from_raw_email(cls, raw_email: RawEmail) -> "SafeEmail":
        """
        Extract PII and create SafeEmail using PIIRedactor.

        Processes email body and any attachments with shared PIIRedactor instance
        for consistent PII numbering across all text.
        """
        # Create PIIRedactor instance shared across email + attachments
        redactor = PIIRedactor()

        # Process subject and body
        safe_subject = redactor.process(raw_email.subject)
        safe_body = redactor.process(raw_email.body)

        # Process attachments (if any)
        processed_attachments = []
        for raw_doc in raw_email.attachments:
            # Process attachment text with shared redactor for consistent numbering
            safe_text = redactor.process(raw_doc.raw_text)

            # Create SafeDocument for this attachment
            safe_doc = SafeDocument(
                document_id=raw_doc.document_id,
                filename=raw_doc.filename,
                source_type=raw_doc.source_type,
                safe_text=safe_text,
                document_timestamp=raw_doc.document_timestamp,
                # Note: pii/links from shared redactor,
                # will be duplicated in email-level too
                pii_extracted=redactor.pii.copy(),
                links_extracted=redactor.links.copy(),
                file_size=raw_doc.file_size,
                metadata=raw_doc.metadata,
            )
            processed_attachments.append(safe_doc)

        return cls(
            email_id=raw_email.email_id,
            document_id=raw_email.document_id,
            subject=safe_subject,
            body=safe_body,
            received_date=raw_email.received_date,
            has_attachments=raw_email.has_attachments,
            attachments=processed_attachments,
            pii_extracted=redactor.pii,  # All PII from email + attachments
            links_extracted=redactor.links,  # All links from email + attachments
        )

    def to_document(self) -> SafeDocument:
        """
        Convert email (+ attachments) to single SafeDocument for unified processing.

        Concatenates email body with all attachment texts into one document.
        This enables emails to be processed through the same pipeline as file uploads.
        """
        # Start with email content
        combined_text = f"Subject: {self.subject}\n\n{self.body}"

        # Append each attachment
        for att in self.attachments:
            combined_text += f"\n\n--- Attachment: {att.filename} ---\n{att.safe_text}"

        # PII and links already accumulated in email-level fields
        # (shared PIIRedactor ensured consistent numbering)

        return SafeDocument(
            document_id=self.document_id,
            filename=f"email_{self.email_id}",
            source_type="email",
            safe_text=combined_text,
            document_timestamp=self.received_date,
            pii_extracted=self.pii_extracted.copy(),
            links_extracted=self.links_extracted.copy(),
            metadata={
                "subject": self.subject,
                "has_attachments": self.has_attachments,
                "attachment_count": len(self.attachments),
            },
        )

    def restore_links(self, text: str) -> str:
        """Restore links to redacted text."""
        return PIIRedactor.restore_links(text, self.links_extracted)

    def restore_pii(self, text: str) -> str:
        """Restore PII to redacted text (for authorized use)."""
        return PIIRedactor.restore_pii(text, self.pii_extracted)
