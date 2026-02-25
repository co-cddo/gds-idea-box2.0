"""File triage pipeline for ministerial correspondence processing.

Provides a reusable pipeline that takes a file (local path), runs it
through classification, extraction, and triage, and returns a structured
result ready for downstream consumers (SharePoint lists, logging, etc.).
"""

from box2.pipeline.components import process_invitation, process_submission
from box2.pipeline.models import TriageResult
from box2.pipeline.triage_file import triage_file

__all__ = ["TriageResult", "process_invitation", "process_submission", "triage_file"]
