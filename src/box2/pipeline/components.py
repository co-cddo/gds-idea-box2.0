"""Pipeline components for processing classified documents.

Each component handles one document type: extracting structured data and
(for invitations) running the triage decision. These are independently
callable when the caller already has a SafeDocument and classification.
"""

import logging
from pathlib import Path

from box2.pipeline.models import TriageResult
from box2.triage.exceptions import ExtractionError, TriageError
from box2.triage.invitation_extraction import extract_invitation
from box2.triage.models import (
    DocumentClassification,
    Invitation,
    MinisterPersona,
    NotInvitation,
    NotSubmission,
    SafeDocument,
)
from box2.triage.submission_extraction import extract_submission
from box2.triage.triage import triage_invitation

logger = logging.getLogger(__name__)

# Resolve the default persona file shipped with the package.
_DEFAULT_PERSONA_PATH = str(Path(__file__).resolve().parent.parent / "triage" / "data" / "example_science_minister.json")


async def process_invitation(
    safe_doc: SafeDocument,
    classification: DocumentClassification,
    persona: MinisterPersona | None = None,
) -> TriageResult:
    """Extract an invitation from a document and triage it.

    Runs invitation extraction, then — if a valid invitation is found —
    triages it against the minister's calendar and priorities.

    Args:
        safe_doc: PII-redacted document.
        classification: The document classification result.
        persona: Minister persona for triage. If ``None``, the default
            example persona shipped with the package is loaded.

    Returns:
        TriageResult with invitation and triage_decision populated, or
        not_invitation if the extractor disagreed with the classifier.

    Raises:
        ExtractionError: If the LLM extraction call fails.
        TriageError: If the LLM triage call fails.
    """
    document_id = safe_doc.document_id

    # --- Extract ---
    extraction = await extract_invitation(safe_doc)

    if isinstance(extraction, NotInvitation):
        logger.info(f"Extractor rejected invitation classification for {document_id}: {extraction.reason}")
        return TriageResult(
            document_id=document_id,
            classification=classification,
            not_invitation=extraction,
            status="not_matched",
        )

    invitation: Invitation = extraction
    logger.info(f"Invitation extracted for {document_id}: event_type={invitation.event_type}, host={invitation.host_org}")

    # --- Load persona ---
    if persona is None:
        persona = MinisterPersona.from_json_file(_DEFAULT_PERSONA_PATH)
        logger.info(f"Loaded default persona: {persona.name}")

    # --- Triage ---
    decision = await triage_invitation(invitation, persona)

    logger.info(f"Triage complete for {document_id}: decision={decision.decision}, priority={decision.priority}")

    return TriageResult(
        document_id=document_id,
        classification=classification,
        invitation=invitation,
        triage_decision=decision,
        status="triaged",
    )


async def process_submission(
    safe_doc: SafeDocument,
    classification: DocumentClassification,
) -> TriageResult:
    """Extract a submission from a document.

    Runs submission extraction and returns structured output ready
    for review.

    Args:
        safe_doc: PII-redacted document.
        classification: The document classification result.

    Returns:
        TriageResult with submission populated, or not_submission if the
        extractor disagreed with the classifier.

    Raises:
        ExtractionError: If the LLM extraction call fails.
    """
    document_id = safe_doc.document_id

    extraction = await extract_submission(safe_doc)

    if isinstance(extraction, NotSubmission):
        logger.info(f"Extractor rejected submission classification for {document_id}: {extraction.reason}")
        return TriageResult(
            document_id=document_id,
            classification=classification,
            not_submission=extraction,
            status="not_matched",
        )

    logger.info(
        f"Submission extracted for {document_id}: policy_area={extraction.policy_area}, "
        f"urgency={extraction.urgency}"
    )

    return TriageResult(
        document_id=document_id,
        classification=classification,
        submission=extraction,
        status="extracted",
    )
