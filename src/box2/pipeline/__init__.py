"""File triage pipeline for ministerial correspondence processing.

Provides a reusable pipeline that takes a file (local path), runs it
through classification, extraction, and triage, and returns a structured
result ready for downstream consumers (SharePoint lists, logging, etc.).
"""

from box2.pipeline.components import process_invitation, process_submission
from box2.pipeline.mappers import to_sharepoint_fields, to_sharepoint_invitation, to_sharepoint_submission
from box2.pipeline.models import TriagedInvitation
from box2.pipeline.triage_file import TriageFileResult, triage_file

__all__ = [
    "TriageFileResult",
    "TriagedInvitation",
    "process_invitation",
    "process_submission",
    "to_sharepoint_fields",
    "to_sharepoint_invitation",
    "to_sharepoint_submission",
    "triage_file",
]
