from __future__ import annotations

from enum import Enum


class ExperimentStatus(str, Enum):
    DRAFT = "draft"
    RUNNING = "running"
    ENDED = "ended"
