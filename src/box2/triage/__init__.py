"""box2.triage — AI-powered document classification, extraction, and triage.

Modules that depend on ``pydantic-ai`` (the AI agent framework) are
lazy-loaded so that consumers who only need models or utility functions
can ``import box2.triage`` without installing the heavy AI dependency
tree.  The public API is unchanged — ``from box2.triage import
classify_document`` still works, but the import of ``pydantic_ai`` is
deferred until that symbol is first accessed.
"""

import importlib

from box2.triage.calendar import MockCalendar, get_calendar_events
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
from box2.triage.pii_redaction import PIIRedactor

# ---------------------------------------------------------------------------
# Lazy imports — these modules depend on pydantic-ai and are only loaded when
# their symbols are first accessed.
# ---------------------------------------------------------------------------

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "extract_actions": ("box2.triage.action_extraction", "extract_actions"),
    "model": ("box2.triage.config", "model"),
    "classify_document": ("box2.triage.document_classifier", "classify_document"),
    "extract_invitation": ("box2.triage.invitation_extraction", "extract_invitation"),
    "redraft_invitation_response": ("box2.triage.invitation_redraft", "redraft_invitation_response"),
    "extract_submission": ("box2.triage.submission_extraction", "extract_submission"),
    "generate_submission_reply": ("box2.triage.submission_reply", "generate_submission_reply"),
    "triage_invitation": ("box2.triage.triage", "triage_invitation"),
}


def __getattr__(name: str):
    if name in _LAZY_IMPORTS:
        module_path, attr = _LAZY_IMPORTS[name]
        mod = importlib.import_module(module_path)
        return getattr(mod, attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Core pipeline functions (lazy)
    "classify_document",
    "extract_invitation",
    "extract_submission",
    "extract_text_from_file",
    "triage_invitation",
    # Post-decision functions (lazy)
    "extract_actions",
    "generate_submission_reply",
    "redraft_invitation_response",
    # Utilities (eager)
    "PIIRedactor",
    "MockCalendar",
    "get_calendar_events",
    "model",
    # Exceptions (eager)
    "CalendarError",
    "ClassificationError",
    "ExtractionError",
    "PersonaError",
    "SubmissionExtractionError",
    "TriageBaseError",
    "TriageError",
]
