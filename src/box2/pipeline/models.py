"""Result models for the file triage pipeline."""

from typing import Literal

from pydantic import BaseModel, Field

from box2.triage.models import (
    DocumentClassification,
    Invitation,
    NotInvitation,
    NotSubmission,
    Submission,
    TriagedDecision,
)


class TriageResult(BaseModel):
    """Complete output of the file triage pipeline.

    Captures every stage of processing so callers can inspect intermediate
    results (e.g. classification) even when extraction or triage was skipped
    or returned a negative match.

    Attributes:
        document_id: Deterministic hash ID linking back to the source file.
        classification: LLM classification of the document type.
        invitation: Extracted invitation details, if classified as invitation.
        not_invitation: Reason the extractor rejected an invitation classification.
        triage_decision: Triage recommendation, populated only when an invitation
            was successfully extracted and triaged.
        submission: Extracted submission details, if classified as submission.
        not_submission: Reason the extractor rejected a submission classification.
        status: Summary of how far the pipeline progressed.
    """

    document_id: str = Field(description="Deterministic ID from source file content hash")

    classification: DocumentClassification = Field(description="LLM document classification result")

    # Invitation path
    invitation: Invitation | None = Field(default=None, description="Extracted invitation, if applicable")
    not_invitation: NotInvitation | None = Field(
        default=None, description="Rejection reason if extractor disagreed with classifier"
    )
    triage_decision: TriagedDecision | None = Field(
        default=None, description="Triage recommendation for the invitation"
    )

    # Submission path
    submission: Submission | None = Field(default=None, description="Extracted submission, if applicable")
    not_submission: NotSubmission | None = Field(
        default=None, description="Rejection reason if extractor disagreed with classifier"
    )

    status: Literal["triaged", "extracted", "classified_only", "not_matched"] = Field(
        description=(
            "'triaged' = invitation fully triaged; "
            "'extracted' = submission extracted (no triage step); "
            "'classified_only' = document type was 'other', no extraction attempted; "
            "'not_matched' = extractor disagreed with classifier"
        )
    )
