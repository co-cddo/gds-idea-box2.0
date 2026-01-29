import hashlib
import re
from datetime import datetime
from typing import Any

import pandas as pd
from dateutil import parser
from pydantic import BaseModel


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
        """Create SafeEmail by extracting PII and links from RawEmail."""
        # Extract PII
        pii = cls._extract_pii(raw_email.subject, raw_email.body)

        # Extract links
        links = cls._extract_links(raw_email.subject, raw_email.body)

        # Redact PII first, then links
        safe_subject = cls._redact_pii(raw_email.subject, pii)
        safe_subject = cls._redact_links(safe_subject, links)

        safe_body = cls._redact_pii(raw_email.body, pii)
        safe_body = cls._redact_links(safe_body, links)

        return cls(
            email_id=raw_email.email_id,
            subject=safe_subject,
            body=safe_body,
            received_date=raw_email.received_date,
            has_attachments=raw_email.has_attachments,
            pii_extracted=pii,
            links_extracted=links,
        )

    @staticmethod
    def _extract_links(subject: str, body: str) -> list[dict[str, str]]:
        """Extract URLs and create domain-visible placeholders."""
        text = f"{subject} {body}"
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = list(set(re.findall(url_pattern, text)))

        links = []
        for i, url in enumerate(urls):
            # Extract domain
            domain_match = re.search(r"https?://([^/]+)", url)
            domain = domain_match.group(1) if domain_match else "unknown"

            links.append({"placeholder": f"[LINK_{i}: {domain}]", "url": url})

        return links

    @staticmethod
    def _redact_links(text: str, links: list[dict[str, str]]) -> str:
        """Replace URLs with domain-visible placeholders."""
        redacted = text
        for link in links:
            redacted = redacted.replace(link["url"], link["placeholder"])
        return redacted

    def restore_links(self, text: str) -> str:
        """Restore links to redacted text."""
        restored = text
        for link in self.links_extracted:
            restored = restored.replace(link["placeholder"], link["url"])
        return restored

    @staticmethod
    def _extract_pii(subject: str, body: str) -> dict[str, list[str]]:
        """Extract PII from text. Returns dict of PII types to values."""
        import re

        text = f"{subject} {body}"
        pii = {
            "emails": [],
            "phone_numbers": [],
            "names": [],  # TODO: Add NER for name detection
        }

        # Extract email addresses
        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        pii["emails"] = list(set(re.findall(email_pattern, text)))

        # Extract UK phone numbers (basic pattern)
        phone_pattern = r"(?:\b0\d{10}\b|\+44\d{10}\b)"
        pii["phone_numbers"] = list(set(re.findall(phone_pattern, text)))

        return pii

    @staticmethod
    def _redact_pii(text: str, pii: dict[str, list[str]]) -> str:
        """Redact PII from text with placeholders."""
        redacted = text

        # Redact emails
        for i, email in enumerate(pii["emails"]):
            redacted = redacted.replace(email, f"[EMAIL_{i}]")

        # Redact phone numbers
        for i, phone in enumerate(pii["phone_numbers"]):
            redacted = redacted.replace(phone, f"[PHONE_{i}]")

        return redacted

    def restore_pii(self, text: str) -> str:
        """Restore PII to redacted text (for authorized use)."""
        restored = text

        for i, email in enumerate(self.pii_extracted["emails"]):
            restored = restored.replace(f"[EMAIL_{i}]", email)

        for i, phone in enumerate(self.pii_extracted["phone_numbers"]):
            restored = restored.replace(f"[PHONE_{i}]", phone)

        return restored
