from __future__ import annotations


class EtlError(Exception):
    pass


class FatalEtlError(EtlError):
    pass


class CheckpointCorruptedError(EtlError):
    def __init__(self, path: str, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(
            f"Checkpoint file '{path}' is corrupted: {reason}"
        )


class StageNotReachableError(EtlError):
    def __init__(self, stage: str, completed_stage: str) -> None:
        self.stage = stage
        self.completed_stage = completed_stage
        super().__init__(
            f"Cannot run stage '{stage}': "
            f"checkpoint indicates '{completed_stage}' already completed."
        )
