"""
Tests for PIIRedactor class.
"""

import pytest

from invitation_triage.pii_redaction import PIIRedactor


# ============================================================================
# Email Extraction Tests
# ============================================================================


def test_extract_pii_single_email():
    """Test extracting a single email address."""
    text = "Meeting with john.doe@example.com. Please contact me."

    pii = PIIRedactor.extract_pii(text)

    assert len(pii["emails"]) == 1
    assert "john.doe@example.com" in pii["emails"]
    assert len(pii["phone_numbers"]) == 0


def test_extract_pii_multiple_emails():
    """Test extracting multiple email addresses."""
    text = "Reach out to alice@test.com or bob@example.org for details."

    pii = PIIRedactor.extract_pii(text)

    assert len(pii["emails"]) == 2
    assert "alice@test.com" in pii["emails"]
    assert "bob@example.org" in pii["emails"]


def test_extract_pii_no_emails():
    """Test text with no email addresses."""
    text = "This is just a regular message with no contact info."

    pii = PIIRedactor.extract_pii(text)

    assert len(pii["emails"]) == 0
    assert len(pii["phone_numbers"]) == 0


def test_extract_pii_duplicate_emails():
    """Test that duplicate emails are deduplicated."""
    text = "Contact john@example.com. Please email john@example.com for more information."

    pii = PIIRedactor.extract_pii(text)

    assert len(pii["emails"]) == 1
    assert "john@example.com" in pii["emails"]


# ============================================================================
# Phone Number Extraction Tests
# ============================================================================


def test_extract_pii_uk_phone_number():
    """Test extracting UK phone number."""
    text = "Call me on 07700900123"

    pii = PIIRedactor.extract_pii(text)

    assert len(pii["phone_numbers"]) == 1
    assert "07700900123" in pii["phone_numbers"]


def test_extract_pii_uk_international_format():
    """Test extracting UK phone in international format."""
    text = "Phone: +447700900123"

    pii = PIIRedactor.extract_pii(text)

    assert len(pii["phone_numbers"]) == 1
    assert "+447700900123" in pii["phone_numbers"]


def test_extract_pii_multiple_phones():
    """Test extracting multiple phone numbers."""
    text = "Contact 07700900123 or +447700900456"

    pii = PIIRedactor.extract_pii(text)

    assert len(pii["phone_numbers"]) == 2


def test_extract_pii_emails_and_phones():
    """Test extracting both emails and phone numbers."""
    text = "Email: support@example.com, Phone: 07700900123"

    pii = PIIRedactor.extract_pii(text)

    assert len(pii["emails"]) == 1
    assert len(pii["phone_numbers"]) == 1
    assert "support@example.com" in pii["emails"]
    assert "07700900123" in pii["phone_numbers"]


# ============================================================================
# Link Extraction Tests
# ============================================================================


def test_extract_links_single_url():
    """Test extracting a single URL."""
    text = "Visit https://example.com for more info"

    links = PIIRedactor.extract_links(text)

    assert len(links) == 1
    assert links[0]["url"] == "https://example.com"
    assert "example.com" in links[0]["placeholder"]


def test_extract_links_multiple_urls():
    """Test extracting multiple URLs."""
    text = "Visit https://example.com and https://test.org for details"

    links = PIIRedactor.extract_links(text)

    assert len(links) == 2
    urls = [link["url"] for link in links]
    assert "https://example.com" in urls
    assert "https://test.org" in urls


def test_extract_links_with_paths():
    """Test extracting URLs with paths."""
    text = "See https://example.com/path/to/page?param=value"

    links = PIIRedactor.extract_links(text)

    assert len(links) == 1
    assert links[0]["url"] == "https://example.com/path/to/page?param=value"
    assert "example.com" in links[0]["placeholder"]


def test_extract_links_http_and_https():
    """Test extracting both HTTP and HTTPS URLs."""
    text = "Visit http://old.com and https://new.com"

    links = PIIRedactor.extract_links(text)

    assert len(links) == 2


def test_extract_links_placeholder_format():
    """Test that link placeholders include domain and index."""
    text = "Visit https://example.com"

    links = PIIRedactor.extract_links(text)

    assert links[0]["placeholder"].startswith("[LINK_")
    assert "example.com" in links[0]["placeholder"]
    assert links[0]["placeholder"].endswith("]")


# ============================================================================
# PII Redaction Tests
# ============================================================================


def test_redact_pii_emails():
    """Test redacting email addresses."""
    text = "Contact alice@test.com or bob@example.org"
    pii = {
        "emails": ["alice@test.com", "bob@example.org"],
        "phone_numbers": [],
    }

    redacted = PIIRedactor.redact_pii(text, pii)

    assert "alice@test.com" not in redacted
    assert "bob@example.org" not in redacted
    assert "[EMAIL_0]" in redacted
    assert "[EMAIL_1]" in redacted


def test_redact_pii_phones():
    """Test redacting phone numbers."""
    text = "Call 07700900123 for assistance"
    pii = {
        "emails": [],
        "phone_numbers": ["07700900123"],
    }

    redacted = PIIRedactor.redact_pii(text, pii)

    assert "07700900123" not in redacted
    assert "[PHONE_0]" in redacted


def test_redact_pii_mixed():
    """Test redacting both emails and phones."""
    text = "Email: support@example.com, Phone: 07700900123"
    pii = {
        "emails": ["support@example.com"],
        "phone_numbers": ["07700900123"],
    }

    redacted = PIIRedactor.redact_pii(text, pii)

    assert "support@example.com" not in redacted
    assert "07700900123" not in redacted
    assert "[EMAIL_0]" in redacted
    assert "[PHONE_0]" in redacted


def test_redact_pii_empty():
    """Test redacting with no PII."""
    text = "This is a normal message"
    pii = {"emails": [], "phone_numbers": []}

    redacted = PIIRedactor.redact_pii(text, pii)

    assert redacted == text


# ============================================================================
# Link Redaction Tests
# ============================================================================


def test_redact_links_single():
    """Test redacting a single link."""
    text = "Visit https://example.com for info"
    links = [{"url": "https://example.com", "placeholder": "[LINK_0: example.com]"}]

    redacted = PIIRedactor.redact_links(text, links)

    assert "https://example.com" not in redacted
    assert "[LINK_0: example.com]" in redacted


def test_redact_links_multiple():
    """Test redacting multiple links."""
    text = "Visit https://example.com and https://test.org"
    links = [
        {"url": "https://example.com", "placeholder": "[LINK_0: example.com]"},
        {"url": "https://test.org", "placeholder": "[LINK_1: test.org]"},
    ]

    redacted = PIIRedactor.redact_links(text, links)

    assert "https://example.com" not in redacted
    assert "https://test.org" not in redacted
    assert "[LINK_0: example.com]" in redacted
    assert "[LINK_1: test.org]" in redacted


# ============================================================================
# Full Process Tests
# ============================================================================


def test_process_complete_workflow():
    """Test the complete stateful process() method."""
    redactor = PIIRedactor()

    subject = "Meeting Request"
    body = "Contact john@example.com, call 07700900123 or visit https://example.com"

    safe_subject = redactor.process(subject)
    safe_body = redactor.process(body)

    # Check subject has no PII
    assert safe_subject == subject

    # Check body is redacted
    assert "john@example.com" not in safe_body
    assert "07700900123" not in safe_body
    assert "https://example.com" not in safe_body
    assert "[EMAIL_0]" in safe_body
    assert "[PHONE_0]" in safe_body
    assert "[LINK_0:" in safe_body

    # Check PII was extracted
    assert len(redactor.pii["emails"]) == 1
    assert "john@example.com" in redactor.pii["emails"]
    assert len(redactor.pii["phone_numbers"]) == 1
    assert "07700900123" in redactor.pii["phone_numbers"]
    assert len(redactor.links) == 1


def test_process_empty_text():
    """Test process with empty text."""
    redactor = PIIRedactor()

    safe_text = redactor.process("")

    assert safe_text == ""
    assert len(redactor.pii["emails"]) == 0


def test_process_no_pii():
    """Test process with no PII."""
    redactor = PIIRedactor()

    text = "This is just a regular message with no sensitive data."
    safe_text = redactor.process(text)

    assert safe_text == text
    assert len(redactor.pii["emails"]) == 0
    assert len(redactor.pii["phone_numbers"]) == 0
    assert len(redactor.links) == 0


def test_process_shared_pii_across_calls():
    """Test that PII is shared and consistently numbered across multiple process() calls."""
    redactor = PIIRedactor()

    text1 = "Email john@example.com"
    text2 = "Also contact john@example.com and alice@test.com"

    safe1 = redactor.process(text1)
    safe2 = redactor.process(text2)

    # Same email gets same placeholder in both texts
    assert "[EMAIL_0]" in safe1
    assert "[EMAIL_0]" in safe2  # john@ is EMAIL_0
    assert "[EMAIL_1]" in safe2  # alice@ is EMAIL_1

    # Total unique emails
    assert len(redactor.pii["emails"]) == 2
    assert "john@example.com" in redactor.pii["emails"]
    assert "alice@test.com" in redactor.pii["emails"]


# ============================================================================
# Restoration Tests
# ============================================================================


def test_restore_pii_emails():
    """Test restoring redacted emails."""
    text = "Contact [EMAIL_0] or [EMAIL_1]"
    pii_extracted = {
        "emails": ["alice@test.com", "bob@example.org"],
        "phone_numbers": [],
    }

    restored = PIIRedactor.restore_pii(text, pii_extracted)

    assert "[EMAIL_0]" not in restored
    assert "[EMAIL_1]" not in restored
    assert "alice@test.com" in restored
    assert "bob@example.org" in restored


def test_restore_pii_phones():
    """Test restoring redacted phone numbers."""
    text = "Call [PHONE_0] for help"
    pii_extracted = {
        "emails": [],
        "phone_numbers": ["07700900123"],
    }

    restored = PIIRedactor.restore_pii(text, pii_extracted)

    assert "[PHONE_0]" not in restored
    assert "07700900123" in restored


def test_restore_links():
    """Test restoring redacted links."""
    text = "Visit [LINK_0: example.com] for more"
    links_extracted = [
        {"url": "https://example.com", "placeholder": "[LINK_0: example.com]"}
    ]

    restored = PIIRedactor.restore_links(text, links_extracted)

    assert "[LINK_0: example.com]" not in restored
    assert "https://example.com" in restored


def test_restore_pii_mixed():
    """Test restoring mixed PII."""
    text = "Email [EMAIL_0] or call [PHONE_0]"
    pii_extracted = {
        "emails": ["support@example.com"],
        "phone_numbers": ["07700900123"],
    }

    restored = PIIRedactor.restore_pii(text, pii_extracted)

    assert "support@example.com" in restored
    assert "07700900123" in restored


# ============================================================================
# Round-trip Tests
# ============================================================================


def test_round_trip_pii():
    """Test that PII can be redacted and restored correctly."""
    original = "Contact alice@test.com or call 07700900123"

    # Extract
    pii = PIIRedactor.extract_pii(original)

    # Redact
    redacted = PIIRedactor.redact_pii(original, pii)

    # Restore
    restored = PIIRedactor.restore_pii(redacted, pii)

    assert restored == original


def test_round_trip_links():
    """Test that links can be redacted and restored correctly."""
    original = "Visit https://example.com for more info"

    # Extract
    links = PIIRedactor.extract_links(original)

    # Redact
    redacted = PIIRedactor.redact_links(original, links)

    # Restore
    restored = PIIRedactor.restore_links(redacted, links)

    assert restored == original


def test_round_trip_complete():
    """Test complete round-trip with stateful process()."""
    redactor = PIIRedactor()

    original_subject = "Meeting Request"
    original_body = "Contact john@example.com or call 07700900123. Visit https://example.com"

    # Process (extract and redact)
    safe_subject = redactor.process(original_subject)
    safe_body = redactor.process(original_body)

    # Restore PII
    restored_body = PIIRedactor.restore_pii(safe_body, redactor.pii)
    restored_body = PIIRedactor.restore_links(restored_body, redactor.links)

    assert restored_body == original_body
