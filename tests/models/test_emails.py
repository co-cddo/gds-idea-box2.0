"""
Tests for data models.
"""

from datetime import datetime

import pandas as pd
import pytest

from invitation_triage.models import RawEmail, SafeEmail

# ============================================================================
# RawEmail Tests
# ============================================================================


def test_create_raw_email_directly():
    """Test creating RawEmail with all fields."""
    email = RawEmail(
        email_id="test123",
        subject="Test Subject",
        body="Test body content",
        received_date=datetime(2026, 1, 15, 10, 30),
        has_attachments=True,
    )

    assert email.email_id == "test123"
    assert email.subject == "Test Subject"
    assert email.body == "Test body content"
    assert email.received_date == datetime(2026, 1, 15, 10, 30)
    assert email.has_attachments is True


def test_raw_email_from_dict_with_email_id():
    """Test creating RawEmail from dict with email_id provided."""
    data = {
        "email_id": "provided_id",
        "subject": "Meeting Request",
        "body": "Let's meet next week",
        "received_date": "2026-01-20 09:15:00",
        "has_attachments": False,
    }

    email = RawEmail.from_dict(data)

    assert email.email_id == "provided_id"
    assert email.subject == "Meeting Request"
    assert isinstance(email.received_date, datetime)


def test_raw_email_from_dict_generates_id():
    """Test that from_dict generates email_id if not provided."""
    data = {
        "subject": "Test",
        "body": "Content",
        "received_date": "2026-01-20 09:15:00",
    }

    email = RawEmail.from_dict(data)

    assert email.email_id is not None
    assert len(email.email_id) == 16  # Our hash length


def test_raw_email_from_dict_parses_date_string():
    """Test that from_dict parses date strings."""
    data = {
        "email_id": "test",
        "subject": "Test",
        "body": "Content",
        "received_date": "2026-01-20 14:30:00",
    }

    email = RawEmail.from_dict(data)

    assert isinstance(email.received_date, datetime)
    assert email.received_date.year == 2026
    assert email.received_date.month == 1
    assert email.received_date.day == 20


def test_raw_email_from_dataframe_row():
    """Test creating RawEmail from pandas DataFrame row."""
    df = pd.DataFrame(
        {
            "Subject": ["Invitation: AI Summit"],
            "Body": ["Please join us for an AI safety discussion."],
            "Received date and time": ["2026-01-20 09:15:00"],
            "Has attachments": ["False"],
        }
    )

    email = RawEmail.from_dataframe_row(df.iloc[0])

    assert email.subject == "Invitation: AI Summit"
    assert "AI safety discussion" in email.body
    assert email.has_attachments is False
    assert isinstance(email.received_date, datetime)


def test_raw_email_generate_id_is_stable():
    """Test that same content generates same ID."""
    id1 = RawEmail._generate_id("Subject", "Body", "2026-01-20")
    id2 = RawEmail._generate_id("Subject", "Body", "2026-01-20")

    assert id1 == id2


def test_raw_email_generate_id_is_different_for_different_content():
    """Test that different content generates different IDs."""
    id1 = RawEmail._generate_id("Subject1", "Body", "2026-01-20")
    id2 = RawEmail._generate_id("Subject2", "Body", "2026-01-20")

    assert id1 != id2


def test_raw_email_outlook_api_not_implemented():
    """Test that Outlook API constructor raises NotImplementedError."""
    with pytest.raises(NotImplementedError):
        RawEmail.from_outlook_api({})


def test_raw_email_gmail_api_not_implemented():
    """Test that Gmail API constructor raises NotImplementedError."""
    with pytest.raises(NotImplementedError):
        RawEmail.from_gmail_api({})


# ============================================================================
# SafeEmail Tests
# ============================================================================


def test_safe_email_extract_email_addresses():
    """Test extraction of email addresses from text."""
    raw = RawEmail(
        email_id="test",
        subject="Contact info",
        body="Please email me at john.doe@example.com or jane@test.org",
        received_date=datetime.now(),
    )

    safe = SafeEmail.from_raw_email(raw)

    assert len(safe.pii_extracted["emails"]) == 2
    assert "john.doe@example.com" in safe.pii_extracted["emails"]
    assert "jane@test.org" in safe.pii_extracted["emails"]


def test_safe_email_extract_phone_numbers():
    """Test extraction of UK phone numbers."""
    raw = RawEmail(
        email_id="test",
        subject="Call me",
        body="Ring me on 07700900123 or +447700900456",
        received_date=datetime.now(),
    )

    safe = SafeEmail.from_raw_email(raw)

    assert len(safe.pii_extracted["phone_numbers"]) == 2


def test_safe_email_redact_email_addresses():
    """Test that email addresses are redacted."""
    raw = RawEmail(
        email_id="test",
        subject="Contact john.doe@example.com",
        body="Email john.doe@example.com for details",
        received_date=datetime.now(),
    )

    safe = SafeEmail.from_raw_email(raw)

    assert "john.doe@example.com" not in safe.subject
    assert "john.doe@example.com" not in safe.body
    assert "[EMAIL_0]" in safe.subject
    assert "[EMAIL_0]" in safe.body


def test_safe_email_redact_phone_numbers():
    """Test that phone numbers are redacted."""
    raw = RawEmail(
        email_id="test",
        subject="Call 07700900123",
        body="Phone: 07700900123",
        received_date=datetime.now(),
    )

    safe = SafeEmail.from_raw_email(raw)

    assert "07700900123" not in safe.subject
    assert "07700900123" not in safe.body
    assert "[PHONE_0]" in safe.subject


def test_safe_email_restore_pii():
    """Test restoring PII to redacted text."""
    raw = RawEmail(
        email_id="test",
        subject="Contact me",
        body="Email: john@example.com or call 07700900123",
        received_date=datetime.now(),
    )

    safe = SafeEmail.from_raw_email(raw)

    # Restore the body
    restored = safe.restore_pii(safe.body)

    assert "john@example.com" in restored
    assert "07700900123" in restored
    assert "[EMAIL_" not in restored
    assert "[PHONE_" not in restored


def test_safe_email_no_pii():
    """Test handling email with no PII."""
    raw = RawEmail(
        email_id="test",
        subject="General announcement",
        body="The meeting is scheduled for next Tuesday.",
        received_date=datetime.now(),
    )

    safe = SafeEmail.from_raw_email(raw)

    assert len(safe.pii_extracted["emails"]) == 0
    assert len(safe.pii_extracted["phone_numbers"]) == 0
    assert safe.subject == raw.subject  # No changes
    assert safe.body == raw.body  # No changes

    # ============================================================================


# SafeEmail Link Extraction Tests
# ============================================================================


def test_safe_email_extract_single_link():
    """Test extraction of a single URL."""
    raw = RawEmail(
        email_id="test",
        subject="Visit our website",
        body="Please visit https://example.com/events for details",
        received_date=datetime.now(),
    )

    safe = SafeEmail.from_raw_email(raw)

    assert len(safe.links_extracted) == 1
    assert safe.links_extracted[0]["url"] == "https://example.com/events"
    assert "example.com" in safe.links_extracted[0]["placeholder"]


def test_safe_email_extract_multiple_links():
    """Test extraction of multiple URLs."""
    raw = RawEmail(
        email_id="test",
        subject="Resources",
        body="Visit https://example.com and https://test.org/page for more info",
        received_date=datetime.now(),
    )

    safe = SafeEmail.from_raw_email(raw)

    assert len(safe.links_extracted) == 2
    urls = [link["url"] for link in safe.links_extracted]
    assert "https://example.com" in urls
    assert "https://test.org/page" in urls


def test_safe_email_redact_links_with_domain_visible():
    """Test that links are redacted with domain visible in placeholder."""
    raw = RawEmail(
        email_id="test",
        subject="Check out the link",
        body="Visit https://example.com/very/long/path?param=value for details",
        received_date=datetime.now(),
    )

    safe = SafeEmail.from_raw_email(raw)

    # Original URL should not be in text
    assert "https://example.com/very/long/path?param=value" not in safe.body

    # Should have placeholder with domain
    assert "[LINK_0: example.com]" in safe.body


def test_safe_email_restore_links():
    """Test restoring links to redacted text."""
    raw = RawEmail(
        email_id="test",
        subject="Link test",
        body="Visit https://example.com for more information",
        received_date=datetime.now(),
    )

    safe = SafeEmail.from_raw_email(raw)

    # Restore links in the body
    restored = safe.restore_links(safe.body)

    assert "https://example.com" in restored
    assert "[LINK_" not in restored


def test_safe_email_no_links():
    """Test handling email with no links."""
    raw = RawEmail(
        email_id="test",
        subject="No links here",
        body="Just plain text with no URLs",
        received_date=datetime.now(),
    )

    safe = SafeEmail.from_raw_email(raw)

    assert len(safe.links_extracted) == 0
    assert safe.body == raw.body  # No changes


def test_safe_email_pii_and_links_separate():
    """Test that PII and links are extracted separately."""
    raw = RawEmail(
        email_id="test",
        subject="Contact info",
        body="Email john@example.com or visit https://example.com/contact",
        received_date=datetime.now(),
    )

    safe = SafeEmail.from_raw_email(raw)

    # Should have both PII and links
    assert len(safe.pii_extracted["emails"]) == 1
    assert len(safe.links_extracted) == 1

    # Both should be redacted
    assert "john@example.com" not in safe.body
    assert "https://example.com/contact" not in safe.body
    assert "[EMAIL_0]" in safe.body
    assert "[LINK_0: example.com]" in safe.body


def test_safe_email_restore_pii_and_links():
    """Test restoring both PII and links."""
    raw = RawEmail(
        email_id="test",
        subject="Full contact",
        body="Email john@example.com or visit https://example.com",
        received_date=datetime.now(),
    )

    safe = SafeEmail.from_raw_email(raw)

    # Restore both (order matters - do what was redacted last, first)
    restored = safe.restore_links(safe.body)
    restored = safe.restore_pii(restored)

    assert "john@example.com" in restored
    assert "https://example.com" in restored
    assert "[EMAIL_" not in restored
    assert "[LINK_" not in restored


def test_safe_email_duplicate_links_deduplicated():
    """Test that duplicate URLs are only stored once."""
    raw = RawEmail(
        email_id="test",
        subject="Duplicate links",
        body="Visit https://example.com here and https://example.com again",
        received_date=datetime.now(),
    )

    safe = SafeEmail.from_raw_email(raw)

    # Should only have one unique link
    assert len(safe.links_extracted) == 1


def test_safe_email_http_and_https():
    """Test extraction of both HTTP and HTTPS URLs."""
    raw = RawEmail(
        email_id="test",
        subject="Mixed protocols",
        body="Visit http://example.com and https://secure.com",
        received_date=datetime.now(),
    )

    safe = SafeEmail.from_raw_email(raw)

    assert len(safe.links_extracted) == 2
    urls = [link["url"] for link in safe.links_extracted]
    assert any("http://example.com" in url for url in urls)
    assert any("https://secure.com" in url for url in urls)


def test_safe_email_long_tracking_url():
    """Test that long tracking URLs are properly shortened."""
    raw = RawEmail(
        email_id="test",
        subject="Newsletter",
        body="Click here: https://example.com/newsletter?utm_source=email&utm_medium=campaign&utm_campaign=jan2026&id=abc123&token=xyz789",
        received_date=datetime.now(),
    )

    safe = SafeEmail.from_raw_email(raw)

    # Long URL should be replaced with short placeholder
    assert len(safe.body) < len(raw.body)
    assert "[LINK_0: example.com]" in safe.body

    # Can restore the full URL
    restored = safe.restore_links(safe.body)
    assert "utm_source=email" in restored


# ============================================================================
# Attachment Tests
# ============================================================================


def test_safe_email_with_no_attachments():
    """Test SafeEmail with empty attachments list (backward compatibility)."""
    raw_email = RawEmail(
        email_id="test",
        subject="Test Subject",
        body="Test body",
        received_date=datetime(2026, 1, 15, 10, 0),
        has_attachments=False,
    )

    safe_email = SafeEmail.from_raw_email(raw_email)

    assert safe_email.attachments == []
    assert len(safe_email.attachments) == 0


def test_safe_email_with_attachments():
    """Test SafeEmail processes attachments with shared PIIRedactor."""
    from invitation_triage.models.document import RawDocument

    # Create an attachment
    attachment = RawDocument(
        document_id="att-1",
        filename="report.txt",
        source_type="txt",
        raw_text="Contact bob@test.org at +447700900456",
        document_timestamp=datetime(2026, 1, 15, 10, 0),
        file_size=50,
        metadata={},
    )

    raw_email = RawEmail(
        email_id="test",
        subject="Report",
        body="See attached from alice@example.com",
        received_date=datetime(2026, 1, 15, 10, 0),
        has_attachments=True,
        attachments=[attachment],
    )

    safe_email = SafeEmail.from_raw_email(raw_email)

    # Check attachments processed
    assert len(safe_email.attachments) == 1
    assert safe_email.attachments[0].filename == "report.txt"
    assert "[EMAIL_1]" in safe_email.attachments[0].safe_text
    assert "bob@test.org" not in safe_email.attachments[0].safe_text

    # Check PII accumulated from both email and attachment
    assert len(safe_email.pii_extracted["emails"]) == 2
    assert "alice@example.com" in safe_email.pii_extracted["emails"]
    assert "bob@test.org" in safe_email.pii_extracted["emails"]


def test_safe_email_attachment_pii_numbering_consistent():
    """Test that PII numbering is consistent across email body and attachments."""
    from invitation_triage.models.document import RawDocument

    # Email has john@example.com
    # Attachment has john@example.com again (should get same [EMAIL_0] placeholder)
    attachment = RawDocument(
        document_id="att-1",
        filename="doc.txt",
        source_type="txt",
        raw_text="Reply to john@example.com about this",
        document_timestamp=datetime(2026, 1, 15, 10, 0),
        file_size=50,
        metadata={},
    )

    raw_email = RawEmail(
        email_id="test",
        subject="Update",
        body="Contact john@example.com for details",
        received_date=datetime(2026, 1, 15, 10, 0),
        has_attachments=True,
        attachments=[attachment],
    )

    safe_email = SafeEmail.from_raw_email(raw_email)

    # Same email should get same placeholder
    assert "[EMAIL_0]" in safe_email.body
    assert "[EMAIL_0]" in safe_email.attachments[0].safe_text

    # Only one unique email in extracted PII
    assert len(safe_email.pii_extracted["emails"]) == 1
    assert "john@example.com" in safe_email.pii_extracted["emails"]


def test_safe_email_to_document_no_attachments():
    """Test converting SafeEmail to SafeDocument (no attachments)."""
    raw_email = RawEmail(
        email_id="test-123",
        subject="Meeting",
        body="Let's meet tomorrow",
        received_date=datetime(2026, 1, 15, 10, 0),
        has_attachments=False,
    )

    safe_email = SafeEmail.from_raw_email(raw_email)
    safe_doc = safe_email.to_document()

    # Check SafeDocument fields
    assert safe_doc.document_id == "test-123"
    assert safe_doc.source_type == "email"
    assert safe_doc.filename == "email_test-123"
    assert "Subject: Meeting" in safe_doc.safe_text
    assert "Let's meet tomorrow" in safe_doc.safe_text
    assert safe_doc.metadata["subject"] == "Meeting"
    assert safe_doc.metadata["has_attachments"] is False
    assert safe_doc.metadata["attachment_count"] == 0


def test_safe_email_to_document_with_attachments():
    """Test converting SafeEmail with attachments to unified SafeDocument."""
    from invitation_triage.models.document import RawDocument

    attachment1 = RawDocument(
        document_id="att-1",
        filename="report.txt",
        source_type="txt",
        raw_text="First attachment content",
        document_timestamp=datetime(2026, 1, 15, 10, 0),
        file_size=50,
        metadata={},
    )

    attachment2 = RawDocument(
        document_id="att-2",
        filename="data.txt",
        source_type="txt",
        raw_text="Second attachment content",
        document_timestamp=datetime(2026, 1, 15, 10, 0),
        file_size=50,
        metadata={},
    )

    raw_email = RawEmail(
        email_id="test-456",
        subject="Report and Data",
        body="Please review the attached files",
        received_date=datetime(2026, 1, 15, 10, 0),
        has_attachments=True,
        attachments=[attachment1, attachment2],
    )

    safe_email = SafeEmail.from_raw_email(raw_email)
    safe_doc = safe_email.to_document()

    # Check document contains email body
    assert "Subject: Report and Data" in safe_doc.safe_text
    assert "Please review the attached files" in safe_doc.safe_text

    # Check document contains both attachments
    assert "--- Attachment: report.txt ---" in safe_doc.safe_text
    assert "First attachment content" in safe_doc.safe_text
    assert "--- Attachment: data.txt ---" in safe_doc.safe_text
    assert "Second attachment content" in safe_doc.safe_text

    # Check metadata
    assert safe_doc.metadata["has_attachments"] is True
    assert safe_doc.metadata["attachment_count"] == 2
    assert safe_doc.source_type == "email"
