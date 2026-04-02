"""box2.triage.models — Pydantic models for triage pipeline data.

The ``RawEmail`` and ``SafeEmail`` models are lazy-loaded because
``email.py`` depends on ``pandas`` which is an optional dependency
(installed via ``box2[pipeline]``).  All other models are eagerly
imported so IDE autocompletion works without the optional group.
"""

import importlib

from box2.triage.models.action import (
    Action,
    ActionExtractionResult,
    FinalDraft,
    InvitationResponse,
)
from box2.triage.models.actions_sharepoint import SharepointAction
from box2.triage.models.calendar import CalendarEvent
from box2.triage.models.decision import TriagedDecision
from box2.triage.models.document import (
    DocumentClassification,
    RawDocument,
    SafeDocument,
    generate_document_id,
)
from box2.triage.models.invitation import EventType, Invitation, NotInvitation
from box2.triage.models.invitation_sharepoint import SharepointInvitation
from box2.triage.models.parli_question_sharepoint import SharepointPQs
from box2.triage.models.persona import MinisterPersona
from box2.triage.models.submission import NotSubmission, Submission
from box2.triage.models.submission_reply import (
    SubmissionReply,
    SubmissionResponse,
)
from box2.triage.models.submission_sharepoint import SharepointSubmission

# ---------------------------------------------------------------------------
# Lazy imports — email.py depends on pandas (optional, in box2[pipeline]).
# ---------------------------------------------------------------------------

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "RawEmail": ("box2.triage.models.email", "RawEmail"),
    "SafeEmail": ("box2.triage.models.email", "SafeEmail"),
}


def __getattr__(name: str):
    if name in _LAZY_IMPORTS:
        module_path, attr = _LAZY_IMPORTS[name]
        mod = importlib.import_module(module_path)
        return getattr(mod, attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "Action",
    "ActionExtractionResult",
    "CalendarEvent",
    "DocumentClassification",
    "EventType",
    "FinalDraft",
    "generate_document_id",
    "Invitation",
    "MinisterPersona",
    "NotInvitation",
    "NotSubmission",
    "InvitationResponse",
    "RawDocument",
    "RawEmail",
    "SafeDocument",
    "SafeEmail",
    "SharepointAction",
    "SharepointInvitation",
    "SharepointSubmission",
    "SharepointPQs",
    "Submission",
    "SubmissionReply",
    "SubmissionResponse",
    "TriagedDecision",
]
