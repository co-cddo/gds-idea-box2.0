"""Core file triage pipeline.

Orchestrates the full classify-extract-triage flow for a single file,
returning a structured :class:`TriageResult` without side effects.
"""

import logging

from box2.pipeline.components import process_invitation, process_submission
from box2.pipeline.models import TriageResult
from box2.triage.document_classifier import classify_document
from box2.triage.file_parser import extract_text_from_file
from box2.triage.models import MinisterPersona, SafeDocument

logger = logging.getLogger(__name__)


async def triage_file(
    file_path: str,
    persona: MinisterPersona | None = None,
) -> TriageResult:
    """Run the full triage pipeline on a single file.

    Parses the file, redacts PII, classifies, extracts (invitation or
    submission), and — for invitations — triages against the minister's
    calendar and priorities.

    Args:
        file_path: Path to a local file (PDF, DOCX, or TXT).
        persona: Minister persona for the triage step. If ``None``, the
            default example persona shipped with the package is loaded.

    Returns:
        A :class:`TriageResult` capturing every stage of processing.

    Raises:
        PipelineError: If file parsing or classification fails.
        ExtractionError: If document extraction fails.
        TriageError: If invitation triage fails.
    """
    # ------------------------------------------------------------------
    # Phase 0: Parse file -> RawDocument -> SafeDocument
    # ------------------------------------------------------------------
    raw_document = extract_text_from_file(file_path=file_path)
    document_id = raw_document.document_id

    logger.info(f"Parsed file: id={document_id}, type={raw_document.source_type}, chars={len(raw_document.raw_text)}")

    safe_doc = SafeDocument.from_raw_document(raw_document)

    logger.info(
        f"PII redacted: emails={len(safe_doc.pii_extracted.get('emails', []))}, "
        f"phones={len(safe_doc.pii_extracted.get('phone_numbers', []))}, "
        f"links={len(safe_doc.links_extracted)}"
    )

    # ------------------------------------------------------------------
    # Phase 1: Classify document
    # ------------------------------------------------------------------
    classification = await classify_document(safe_doc)

    logger.info(
        f"Classified {document_id} as '{classification.document_type}' (confidence={classification.confidence:.2f})"
    )

    # ------------------------------------------------------------------
    # Phase 2: Branch on document type
    # ------------------------------------------------------------------
    if classification.document_type == "invitation":
        return await process_invitation(safe_doc, classification, persona)

    if classification.document_type == "submission":
        return await process_submission(safe_doc, classification)

    logger.info(f"Document {document_id} classified as '{classification.document_type}'; no extraction attempted")
    return TriageResult(
        document_id=document_id,
        classification=classification,
        status="classified_only",
    )
