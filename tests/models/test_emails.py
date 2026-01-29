"""
Tests for data models.
"""

from datetime import datetime
import pandas as pd
import pytest

from invitation_triage.models.email import RawEmail, SafeEmail


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
        has_attachments=True
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
        "has_attachments": False
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
        "received_date": "2026-01-20 09:15:00"
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
        "received_date": "2026-01-20 14:30:00"
    }
    
    email = RawEmail.from_dict(data)
    
    assert isinstance(email.received_date, datetime)
    assert email.received_date.year == 2026
    assert email.received_date.month == 1
    assert email.received_date.day == 20


def test_raw_email_from_dataframe_row():
    """Test creating RawEmail from pandas DataFrame row."""
    df = pd.DataFrame({
        'Subject': ['Invitation: AI Summit'],
        'Body': ['Please join us for an AI safety discussion.'],
        'Received date and time': ['2026-01-20 09:15:00'],
        'Has attachments': ['False']
    })
    
    email = RawEmail.from_dataframe_row(df.iloc[0])
    
    assert email.subject == 'Invitation: AI Summit'
    assert 'AI safety discussion' in email.body
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
        received_date=datetime.now()
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
        received_date=datetime.now()
    )
    
    safe = SafeEmail.from_raw_email(raw)
    

    assert len(safe.pii_extracted["phone_numbers"]) == 2


def test_safe_email_redact_email_addresses():
    """Test that email addresses are redacted."""
    raw = RawEmail(
        email_id="test",
        subject="Contact john.doe@example.com",
        body="Email john.doe@example.com for details",
        received_date=datetime.now()
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
        received_date=datetime.now()
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
        received_date=datetime.now()
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
        received_date=datetime.now()
    )
    
    safe = SafeEmail.from_raw_email(raw)
    
    assert len(safe.pii_extracted["emails"]) == 0
    assert len(safe.pii_extracted["phone_numbers"]) == 0
    assert safe.subject == raw.subject  # No changes
    assert safe.body == raw.body  # No changes