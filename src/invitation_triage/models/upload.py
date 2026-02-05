from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ProcessedUpload(BaseModel):
    """
    Processed document ready for classification.

    Contains extracted text and metadata from uploaded file or email.
    Text extraction happens upstream - this model receives the already-extracted text.
    """

    upload_id: str = Field(
        description="Unique identifier for this upload"
    )

    text: str = Field(
        min_length=10,
        description="Extracted text content from document (email body, PDF text, Word doc, etc.)"
    )

    # Metadata fields
    source_type: str | None = Field(
        default=None,
        description="Type of source: 'email', 'pdf', 'docx', 'txt', etc."
    )

    filename: str | None = Field(
        default=None,
        description="Original filename if from file upload"
    )

    subject: str | None = Field(
        default=None,
        description="Email subject line if from email source"
    )

    upload_timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When this document was uploaded/received"
    )

    metadata: dict = Field(
        default_factory=dict,
        description="Additional metadata (sender, attachments, file size, etc.)"
    )


class UploadClassification(BaseModel):
    """
    Result of classifying an upload.

    Determines what type of ministerial document this is for routing to
    appropriate extraction and processing pipelines.
    """

    upload_id: str = Field(
        description="Links back to the ProcessedUpload that was classified"
    )

    document_type: Literal["invitation", "submission", "other"] = Field(
        description="Classified document type. "
        "'invitation' = event attendance request, "
        "'submission' = ministerial submission requesting decision, "
        "'other' = unrecognized or general correspondence"
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score (0.0-1.0) in this classification. "
        "0.9+ = very confident, 0.5-0.7 = ambiguous, <0.5 = low confidence"
    )

    reasoning: str = Field(
        min_length=10,
        description="Brief explanation of why this classification was chosen"
    )
