"""box2.triage — AI-powered document classification, extraction, and triage."""

from box2.triage.action_extraction import extract_actions
from box2.triage.calendar import MockCalendar, get_calendar_events
from box2.triage.config import model
from box2.triage.document_classifier import classify_document
from box2.triage.exceptions import (
    CalendarError,
    ClassificationError,
    ExtractionError,
    PersonaError,
    SubmissionExtractionError,
    TriageBaseError,
    TriageError,
)
from box2.triage.file_parser import extract_text_from_file
from box2.triage.invitation_extraction import extract_invitation
from box2.triage.invitation_redraft import redraft_invitation_response
from box2.triage.pii_redaction import PIIRedactor
from box2.triage.submission_extraction import extract_submission
from box2.triage.submission_reply import generate_submission_reply
from box2.triage.triage import triage_invitation

__all__ = [
    # Core pipeline functions
    "classify_document",
    "extract_invitation",
    "extract_submission",
    "extract_text_from_file",
    "triage_invitation",
    # Post-decision functions
    "extract_actions",
    "generate_submission_reply",
    "redraft_invitation_response",
    # Utilities
    "PIIRedactor",
    "MockCalendar",
    "get_calendar_events",
    "model",
    # Exceptions
    "CalendarError",
    "ClassificationError",
    "ExtractionError",
    "PersonaError",
    "SubmissionExtractionError",
    "TriageBaseError",
    "TriageError",
]
