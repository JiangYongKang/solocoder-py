from __future__ import annotations


class PipelineError(Exception):
    pass


class PipelineTimeoutError(PipelineError):
    def __init__(self, timeout: float) -> None:
        self.timeout = timeout
        super().__init__(f"Pipeline timed out after {timeout} seconds")


class StageError(PipelineError):
    def __init__(self, stage_name: str, message: str) -> None:
        self.stage_name = stage_name
        super().__init__(f"Stage '{stage_name}': {message}")


class ItemRetryExhaustedError(StageError):
    def __init__(self, stage_name: str, item_id: str, attempts: int, last_error: Exception) -> None:
        self.item_id = item_id
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(
            stage_name,
            f"Item '{item_id}' exhausted all {attempts} retry attempts. Last error: {last_error}",
        )


class PipelineCancelledError(PipelineError):
    pass


class InvalidPipelineConfigError(PipelineError):
    pass
