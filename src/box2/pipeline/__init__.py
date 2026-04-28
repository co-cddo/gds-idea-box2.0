"""File triage pipeline for ministerial correspondence processing.

Provides a reusable pipeline that takes a file (local path), runs it
through classification, extraction, and triage, and returns a structured
result ready for downstream consumers (SharePoint lists, logging, etc.).

Modules that depend on ``pydantic-ai`` (``components``, ``triage_file``)
are lazy-loaded so that consumers who only need mappers or models can
import this package without the heavy AI dependency tree.
"""

import importlib

from box2.pipeline.mappers import (
    from_sharepoint_fields,
    to_sharepoint_action,
    to_sharepoint_fields,
    to_sharepoint_invitation,
    to_sharepoint_invitation_qa,
    to_sharepoint_submission,
)
from box2.pipeline.models import ActionReviewResult, TriagedInvitation

# ---------------------------------------------------------------------------
# Lazy imports — these modules depend on pydantic-ai and are only loaded when
# their symbols are first accessed.
# ---------------------------------------------------------------------------

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "extract_actions_from_review": ("box2.pipeline.components", "extract_actions_from_review"),
    "process_invitation": ("box2.pipeline.components", "process_invitation"),
    "process_submission": ("box2.pipeline.components", "process_submission"),
    "TriageFileResult": ("box2.pipeline.triage_file", "TriageFileResult"),
    "triage_file": ("box2.pipeline.triage_file", "triage_file"),
}


def __getattr__(name: str):
    if name in _LAZY_IMPORTS:
        module_path, attr = _LAZY_IMPORTS[name]
        mod = importlib.import_module(module_path)
        return getattr(mod, attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ActionReviewResult",
    "TriageFileResult",
    "TriagedInvitation",
    "extract_actions_from_review",
    "from_sharepoint_fields",
    "process_invitation",
    "process_submission",
    "to_sharepoint_action",
    "to_sharepoint_fields",
    "to_sharepoint_invitation",
    "to_sharepoint_invitation_qa",
    "to_sharepoint_submission",
    "triage_file",
]
