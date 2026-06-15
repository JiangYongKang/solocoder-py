from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


STAGE_EXTRACT: str = "extract"
STAGE_TRANSFORM: str = "transform"
STAGE_LOAD: str = "load"
STAGE_COMPLETED: str = "completed"


@dataclass
class DataRow:
    row_id: int
    data: Any

    def __post_init__(self) -> None:
        if self.row_id < 0:
            raise ValueError("row_id must be non-negative")


@dataclass
class ErrorRecord:
    original_row: DataRow
    stage: str
    error_type: str
    error_message: str
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        valid_stages = {STAGE_EXTRACT, STAGE_TRANSFORM, STAGE_LOAD}
        if self.stage not in valid_stages:
            raise ValueError(
                f"stage must be one of {valid_stages}, got '{self.stage}'"
            )


@dataclass
class Checkpoint:
    job_id: str
    last_completed_stage: str = ""
    rows_extracted: int = 0
    rows_transformed: int = 0
    rows_loaded: int = 0
    rows_failed: int = 0
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_stage_completed(self, stage: str) -> bool:
        order = [STAGE_EXTRACT, STAGE_TRANSFORM, STAGE_LOAD, STAGE_COMPLETED]
        if stage not in order:
            return False
        if self.last_completed_stage == STAGE_COMPLETED:
            return True
        if self.last_completed_stage == "":
            return False
        try:
            completed_idx = order.index(self.last_completed_stage)
            stage_idx = order.index(stage)
        except ValueError:
            return False
        return completed_idx >= stage_idx

    def mark_stage_completed(self, stage: str) -> None:
        valid = {STAGE_EXTRACT, STAGE_TRANSFORM, STAGE_LOAD, STAGE_COMPLETED}
        if stage not in valid:
            raise ValueError(f"Invalid stage: {stage}")
        self.last_completed_stage = stage
        self.updated_at = datetime.now()

    def is_job_completed(self) -> bool:
        return self.last_completed_stage == STAGE_COMPLETED
