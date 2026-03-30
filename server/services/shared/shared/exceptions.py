"""Domain exceptions shared across all microservices.

Services raise these; exception handlers translate to HTTP responses.
"""


class AppError(Exception):
    """Base exception for all application-level errors."""

    def __init__(self, detail: str = "An unexpected error occurred") -> None:
        self.detail = detail
        super().__init__(detail)


class NotFoundError(AppError):
    def __init__(self, detail: str = "Resource not found") -> None:
        super().__init__(detail)


class ConflictError(AppError):
    def __init__(self, detail: str = "Resource already exists") -> None:
        super().__init__(detail)


class UnauthorizedError(AppError):
    def __init__(self, detail: str = "Could not validate credentials") -> None:
        super().__init__(detail)


class ForbiddenError(AppError):
    def __init__(self, detail: str = "Not enough permissions") -> None:
        super().__init__(detail)


class ValidationError(AppError):
    def __init__(self, detail: str = "Validation error") -> None:
        super().__init__(detail)
