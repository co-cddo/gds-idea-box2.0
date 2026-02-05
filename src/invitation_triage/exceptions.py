"""Custom exceptions for invitation triage system."""


class TriageBaseException(Exception):
    """Base exception for invitation triage system."""

    pass


class ExtractionError(TriageBaseException):
    """Error during invitation extraction from email."""

    def __init__(self, message: str, email_id: str | None = None, cause: Exception | None = None):
        self.email_id = email_id
        self.cause = cause
        super().__init__(message)


class TriageError(TriageBaseException):
    """Error during invitation triage decision-making."""

    def __init__(self, message: str, invitation_id: str | None = None, cause: Exception | None = None):
        self.invitation_id = invitation_id
        self.cause = cause
        super().__init__(message)


class CalendarError(TriageBaseException):
    """Error during calendar operations."""

    def __init__(self, message: str, cause: Exception | None = None):
        self.cause = cause
        super().__init__(message)


class PersonaError(TriageBaseException):
    """Error loading or validating minister persona."""

    def __init__(self, message: str, persona_path: str | None = None, cause: Exception | None = None):
        self.persona_path = persona_path
        self.cause = cause
        super().__init__(message)


class SubmissionExtractionError(TriageBaseException):
    """Error during submission extraction from text."""

    def __init__(self, message: str, text_preview: str | None = None, cause: Exception | None = None):
        self.text_preview = text_preview
        self.cause = cause
        super().__init__(message)


class ClassificationError(TriageBaseException):
    """Error during document classification."""

    def __init__(self, message: str, text_preview: str | None = None, cause: Exception | None = None):
        self.text_preview = text_preview
        self.cause = cause
        super().__init__(message)
