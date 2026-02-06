import hashlib
from datetime import datetime
from typing import Any

import pandas as pd
from dateutil import parser
from pydantic import BaseModel

from invitation_triage.pii_redaction import PIIRedactor


class RawEmail(BaseModel):
    """Raw email as ingested from CSV or other source."""

    email_id: str
    subject: str
    body: str
    received_date: datetime
    has_attachments: bool = False

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

    email_id: str
    subject: str  # PII-redacted
    body: str  # PII-redacted
    received_date: datetime
    has_attachments: bool = False
    pii_extracted: dict[str, list[str]]
    links_extracted: list[dict[str, str]]

    @classmethod
    def from_raw_email(cls, raw_email: RawEmail) -> "SafeEmail":
        """Extract PII and create SafeEmail using PIIRedactor."""
        # Create PIIRedactor instance for this email (and potential attachments)
        redactor = PIIRedactor()

        # Process subject
        safe_subject = redactor.process(raw_email.subject)

        # Process body
        safe_body = redactor.process(raw_email.body)

        return cls(
            email_id=raw_email.email_id,
            subject=safe_subject,
            body=safe_body,
            received_date=raw_email.received_date,
            has_attachments=raw_email.has_attachments,
            pii_extracted=redactor.pii,  # Access accumulated PII
            links_extracted=redactor.links,  # Access accumulated links
        )

    def restore_links(self, text: str) -> str:
        """Restore links to redacted text."""
        return PIIRedactor.restore_links(text, self.links_extracted)

    def restore_pii(self, text: str) -> str:
        """Restore PII to redacted text (for authorized use)."""
        return PIIRedactor.restore_pii(text, self.pii_extracted)
