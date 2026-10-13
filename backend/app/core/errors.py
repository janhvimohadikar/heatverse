"""Framework-independent application errors; the API layer converts them to HTTP responses."""


class AppError(Exception):
    status_code = 400

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        if status_code:
            self.status_code = status_code


class NotFoundError(AppError):
    status_code = 404


class ValidationFailed(AppError):
    status_code = 422


class ExternalServiceError(AppError):
    status_code = 502
