from __future__ import annotations


class RetryError(Exception):
    pass


class InvalidRetryStrategyError(RetryError):
    pass


class MaxAttemptsExceededError(RetryError):
    def __init__(self, attempts: int) -> None:
        self.attempts = attempts
        super().__init__(f"Maximum retry attempts exceeded after {attempts} attempts")


class NonRetryableError(RetryError):
    def __init__(self, original_error: Exception) -> None:
        self.original_error = original_error
        super().__init__(f"Non-retryable error encountered: {original_error}")
