"""Custom exception hierarchy for Mem API backend."""


class MemException(Exception):
    """Base exception for all Mem errors."""

    def __init__(self, message: str, error_code: str = "MEM_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(message)


class ValidationError(MemException):
    """Raised for input validation failures."""

    def __init__(self, message: str):
        super().__init__(message, "VALIDATION_ERROR")


class DatabaseError(MemException):
    """Raised for database operation failures."""

    def __init__(self, message: str):
        super().__init__(message, "DATABASE_ERROR")


class ProcessingError(MemException):
    """Raised for video/audio processing failures."""

    def __init__(self, message: str):
        super().__init__(message, "PROCESSING_ERROR")


class ResourceNotFoundError(MemException):
    """Raised when a requested resource doesn't exist."""

    def __init__(self, resource_type: str, resource_id: any):
        super().__init__(f"{resource_type} {resource_id} not found", "NOT_FOUND")
        self.resource_type = resource_type
        self.resource_id = resource_id


class StreamError(MemException):
    """Raised for streaming operation failures."""

    def __init__(self, message: str):
        super().__init__(message, "STREAM_ERROR")
