"""Custom exceptions for invitation triage system."""


class TriageBaseError(Exception):
    """Base exception for invitation triage system."""

    pass


class ExtractionError(TriageBaseError):
    """Error during document extraction."""

    def __init__(
        self,
        message: str,
        document_id: str | None = None,
        cause: Exception | None = None,
    ):
        self.document_id = document_id
        self.cause = cause
        super().__init__(message)


class TriageError(TriageBaseError):
    """Error during invitation triage decision-making."""

    def __init__(
        self,
        message: str,
        document_id: str | None = None,
        cause: Exception | None = None,
    ):
        self.document_id = document_id
        self.cause = cause
        super().__init__(message)


class CalendarError(TriageBaseError):
    """Error during calendar operations."""

    def __init__(self, message: str, cause: Exception | None = None):
        self.cause = cause
        super().__init__(message)


class PersonaError(TriageBaseError):
    """Error loading or validating minister persona."""

    def __init__(
        self,
        message: str,
        persona_path: str | None = None,
        cause: Exception | None = None,
    ):
        self.persona_path = persona_path
        self.cause = cause
        super().__init__(message)


class SubmissionExtractionError(TriageBaseError):
    """Error during submission extraction from text."""

    def __init__(
        self,
        message: str,
        text_preview: str | None = None,
        cause: Exception | None = None,
    ):
        self.text_preview = text_preview
        self.cause = cause
        super().__init__(message)


class ClassificationError(TriageBaseError):
    """Error during document classification."""

    def __init__(
        self,
        message: str,
        text_preview: str | None = None,
        cause: Exception | None = None,
    ):
        self.text_preview = text_preview
        self.cause = cause
        super().__init__(message)
