from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class PositionDecayType(str, Enum):
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    NONE = "none"


class SimilarityMetric(str, Enum):
    JACCARD = "jaccard"
    SHARED_RATIO = "shared_ratio"


@dataclass
class SentenceScore:
    index: int
    text: str
    frequency_score: float
    position_weight: float
    final_score: float
    tokens: list[str] = field(default_factory=list)


@dataclass
class SummarizerConfig:
    num_sentences: int = 3
    position_decay: PositionDecayType = PositionDecayType.LINEAR
    position_weight_factor: float = 0.5
    exponential_decay_rate: float = 0.5
    similarity_metric: SimilarityMetric = SimilarityMetric.JACCARD
    similarity_threshold: float = 0.5
    redundancy_penalty: float = 0.5
    extra_stopwords: Optional[set[str]] = None
