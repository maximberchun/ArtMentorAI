class AIServiceError(Exception):
    """
    Exception for AI service errors (quota, rate limits, unavailable).

    Attributes:
        message (str): A human-readable message to show to the user.
        error_code (str): Error code for categorization (e.g., 'QUOTA_EXCEEDED', 'SERVICE_UNAVAILABLE').
        retry_after (float | None): Seconds to wait before retry, if applicable.
    """

    def __init__(
        self,
        message: str,
        error_code: str = 'AI_SERVICE_ERROR',
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.retry_after = retry_after

    def __str__(self) -> str:
        return self.message
