"""Pipeline components for processing classified documents.

Each component handles one document type: extracting structured data and
(for invitations) running the triage decision. These are independently
callable when the caller already has a SafeDocument.
"""

import logging
from pathlib import Path

from box2.pipeline.models import TriagedInvitation
from box2.triage.invitation_extraction import extract_invitation
from box2.triage.models import (
    Invitation,
    MinisterPersona,
    NotInvitation,
    NotSubmission,
    SafeDocument,
    Submission,
)
from box2.triage.submission_extraction import extract_submission
from box2.triage.triage import triage_invitation

logger = logging.getLogger(__name__)

# Resolve the default persona file shipped with the package.
_DEFAULT_PERSONA_PATH = str(Path(__file__).resolve().parent.parent / "triage" / "data" / "example_science_minister.json")


async def process_invitation(
    safe_doc: SafeDocument,
    persona: MinisterPersona | None = None,
) -> TriagedInvitation | NotInvitation:
    """Extract an invitation from a document and triage it.

    Runs invitation extraction, then — if a valid invitation is found —
    triages it against the minister's calendar and priorities.

    Args:
        safe_doc: PII-redacted document.
        persona: Minister persona for triage. If ``None``, the default
            example persona shipped with the package is loaded.

    Returns:
        TriagedInvitation if extraction and triage succeeded, or
        NotInvitation if the extractor disagreed with the classifier.

    Raises:
        ExtractionError: If the LLM extraction call fails.
        TriageError: If the LLM triage call fails.
    """
    document_id = safe_doc.document_id

    extraction = await extract_invitation(safe_doc)

    if isinstance(extraction, NotInvitation):
        logger.info(f"Extractor rejected invitation classification for {document_id}: {extraction.reason}")
        return extraction

    invitation: Invitation = extraction
    logger.info(f"Invitation extracted for {document_id}: event_type={invitation.event_type}, host={invitation.host_org}")

    # --- Load persona ---
    if persona is None:
        persona = MinisterPersona.from_json_file(_DEFAULT_PERSONA_PATH)
        logger.info(f"Loaded default persona: {persona.name}")

    # --- Triage ---
    decision = await triage_invitation(invitation, persona)

    logger.info(f"Triage complete for {document_id}: decision={decision.decision}, priority={decision.priority}")

    return TriagedInvitation(invitation=invitation, decision=decision)


async def process_submission(
    safe_doc: SafeDocument,
) -> Submission | NotSubmission:
    """Extract a submission from a document.

    Runs submission extraction and returns the result directly.

    Args:
        safe_doc: PII-redacted document.

    Returns:
        Submission if extraction succeeded, or NotSubmission if the
        extractor disagreed with the classifier.

    Raises:
        ExtractionError: If the LLM extraction call fails.
    """
    document_id = safe_doc.document_id

    extraction = await extract_submission(safe_doc)

    if isinstance(extraction, NotSubmission):
        logger.info(f"Extractor rejected submission classification for {document_id}: {extraction.reason}")
        return extraction

    logger.info(
        f"Submission extracted for {document_id}: policy_area={extraction.policy_area}, "
        f"urgency={extraction.urgency}"
    )

    return extraction
