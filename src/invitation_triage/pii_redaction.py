"""
Centralized PII extraction and redaction logic.

This module provides utilities for identifying and redacting personally
identifiable information (PII) from text before processing with LLMs.
"""

import re
from urllib.parse import urlparse


class PIIRedactor:
    """
    Stateful PII extraction and redaction.

    Maintains accumulated PII and link dictionaries across multiple process() calls,
    ensuring consistent placeholder numbering across all processed texts.

    Usage:
        redactor = PIIRedactor()
        safe_text1 = redactor.process(text1)
        safe_text2 = redactor.process(text2)  # Continues numbering from text1

        # Access accumulated PII
        all_pii = redactor.pii
        all_links = redactor.links
    """

    def __init__(self):
        """Initialize empty PII and link tracking."""
        self.pii = {
            "emails": [],
            "phone_numbers": [],
            "names": [],  # TODO: Add NER for name detection
        }
        self.links = []

    def process(self, text: str) -> str:
        """
        Process text: extract PII/links and redact, maintaining state.

        Args:
            text: Text to process (email subject/body, document content, etc.)

        Returns:
            Redacted text with PII/links replaced by placeholders
        """
        # Extract PII from this text
        new_pii = self.extract_pii(text)
        new_links = self.extract_links(text)

        # Merge with accumulated state (maintaining consistent indices)
        self._merge_pii(new_pii)
        self._merge_links(new_links)

        # Redact using ALL accumulated PII/links
        redacted = self.redact_pii(text, self.pii)
        redacted = self.redact_links(redacted, self.links)

        return redacted

    def _merge_pii(self, new_pii: dict[str, list[str]]) -> None:
        """
        Merge new PII into accumulated state, avoiding duplicates.

        Ensures each unique PII value gets a consistent index.
        """
        for key in ["emails", "phone_numbers", "names"]:
            for value in new_pii.get(key, []):
                if value not in self.pii[key]:
                    self.pii[key].append(value)

    def _merge_links(self, new_links: list[dict[str, str]]) -> None:
        """
        Merge new links into accumulated state, avoiding duplicates.

        Ensures each unique URL gets a consistent index.
        """
        existing_urls = {link["url"] for link in self.links}
        for new_link in new_links:
            if new_link["url"] not in existing_urls:
                # Re-index placeholder to match current state
                new_index = len(self.links)
                domain_match = re.search(r"https?://([^/]+)", new_link["url"])
                domain = domain_match.group(1) if domain_match else "unknown"
                self.links.append(
                    {
                        "url": new_link["url"],
                        "placeholder": f"[LINK_{new_index}: {domain}]",
                    }
                )

    @staticmethod
    def extract_pii(text: str) -> dict[str, list[str]]:
        """
        Extract PII from text.

        Args:
            text: Text to scan for PII

        Returns:
            Dict with keys: 'emails', 'phone_numbers', 'names'
        """
        pii = {
            "emails": [],
            "phone_numbers": [],
            "names": [],  # TODO: Add NER for name detection
        }

        # Extract email addresses
        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        pii["emails"] = list(set(re.findall(email_pattern, text)))

        # Extract UK phone numbers (basic pattern)
        # Matches: 0XXXXXXXXXX or +44XXXXXXXXXX
        phone_pattern = r"(?:\b0\d{10}\b|\+44\d{10}\b)"
        pii["phone_numbers"] = list(set(re.findall(phone_pattern, text)))

        return pii

    @staticmethod
    def extract_links(text: str) -> list[dict[str, str]]:
        """
        Extract URLs and create domain-visible placeholders.

        Args:
            text: Text to scan for URLs

        Returns:
            List of dicts with 'placeholder' and 'url' keys
        """
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = list(set(re.findall(url_pattern, text)))

        links = []
        for i, url in enumerate(urls):
            # Extract domain for placeholder
            domain_match = re.search(r"https?://([^/]+)", url)
            domain = domain_match.group(1) if domain_match else "unknown"

            links.append(
                {
                    "placeholder": f"[LINK_{i}: {domain}]",
                    "url": url,
                }
            )

        return links

    @staticmethod
    def redact_pii(text: str, pii: dict[str, list[str]]) -> str:
        """
        Replace PII with placeholders.

        Args:
            text: Text to redact
            pii: Dict of PII from extract_pii()

        Returns:
            Text with PII replaced by placeholders
        """
        redacted = text

        # Redact emails
        for i, email in enumerate(pii["emails"]):
            redacted = redacted.replace(email, f"[EMAIL_{i}]")

        # Redact phone numbers
        for i, phone in enumerate(pii["phone_numbers"]):
            redacted = redacted.replace(phone, f"[PHONE_{i}]")

        return redacted

    @staticmethod
    def redact_links(text: str, links: list[dict[str, str]]) -> str:
        """
        Replace URLs with domain-visible placeholders.

        Args:
            text: Text to redact
            links: List of link dicts from extract_links()

        Returns:
            Text with URLs replaced by placeholders
        """
        redacted = text
        for link in links:
            redacted = redacted.replace(link["url"], link["placeholder"])
        return redacted

    @staticmethod
    def restore_pii(text: str, pii_extracted: dict[str, list[str]]) -> str:
        """
        Restore PII to redacted text (for authorized use).

        Args:
            text: Redacted text with placeholders
            pii_extracted: Dict of extracted PII

        Returns:
            Text with PII placeholders replaced by original values
        """
        restored = text

        for i, email in enumerate(pii_extracted.get("emails", [])):
            restored = restored.replace(f"[EMAIL_{i}]", email)

        for i, phone in enumerate(pii_extracted.get("phone_numbers", [])):
            restored = restored.replace(f"[PHONE_{i}]", phone)

        return restored

    @staticmethod
    def restore_links(text: str, links_extracted: list[dict[str, str]]) -> str:
        """
        Restore links to redacted text.

        Args:
            text: Redacted text with link placeholders
            links_extracted: List of link dicts from extract_links()

        Returns:
            Text with link placeholders replaced by original URLs
        """
        restored = text
        for link in links_extracted:
            restored = restored.replace(link["placeholder"], link["url"])
        return restored
