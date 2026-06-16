from __future__ import annotations

import math
import re
from collections import Counter
from typing import Optional

from .exceptions import (
    SummarizerInvalidInputError,
    SummarizerInvalidParameterError,
)
from .models import (
    PositionDecayType,
    SentenceScore,
    SimilarityMetric,
    SummarizerConfig,
)
from ..fulltext.stopwords import StopWords
from ..fulltext.tokenizer import Tokenizer


_SENTENCE_SPLIT_PATTERN = re.compile(
    r"(?<=[.!?。！？])\s+"
    r"|(?<=[。！？])"
    r"|(?<=[.!?])$"
)


def _split_sentences(text: str) -> list[str]:
    if not text.strip():
        return []
    parts = _SENTENCE_SPLIT_PATTERN.split(text.strip())
    sentences = [s.strip() for s in parts if s.strip()]
    return sentences


def _compute_position_weight(
    index: int,
    total: int,
    decay_type: PositionDecayType,
    decay_rate: float,
    factor: float,
) -> float:
    if total <= 1:
        return 1.0
    if decay_type == PositionDecayType.NONE:
        return 1.0

    mid = (total - 1) / 2.0
    distance_from_center = abs(index - mid) / mid

    if decay_type == PositionDecayType.LINEAR:
        weight = factor + distance_from_center * (1.0 - factor)
    elif decay_type == PositionDecayType.EXPONENTIAL:
        proximity_to_center = 1.0 - distance_from_center
        weight = math.exp(-decay_rate * proximity_to_center)
        weight = factor + (1.0 - factor) * weight
    else:
        weight = 1.0

    return max(weight, factor)


def _jaccard_similarity(tokens_a: set[str], tokens_b: set[str]) -> float:
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = len(tokens_a & tokens_b)
    union = len(tokens_a | tokens_b)
    if union == 0:
        return 0.0
    return intersection / union


def _shared_ratio(tokens_a: set[str], tokens_b: set[str]) -> float:
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = len(tokens_a & tokens_b)
    smaller = min(len(tokens_a), len(tokens_b))
    if smaller == 0:
        return 0.0
    return intersection / smaller


class TextSummarizer:
    def __init__(self, config: Optional[SummarizerConfig] = None) -> None:
        self._config = config or SummarizerConfig()
        self._stopwords = StopWords(self._config.extra_stopwords)
        self._tokenizer = Tokenizer()
        self._validate_config(self._config)

    @staticmethod
    def _validate_config(config: SummarizerConfig) -> None:
        if config.num_sentences < 0:
            raise SummarizerInvalidParameterError(
                "num_sentences must be non-negative"
            )
        if config.similarity_threshold < 0 or config.similarity_threshold > 1:
            raise SummarizerInvalidParameterError(
                "similarity_threshold must be between 0 and 1"
            )
        if config.redundancy_penalty < 0 or config.redundancy_penalty > 1:
            raise SummarizerInvalidParameterError(
                "redundancy_penalty must be between 0 and 1"
            )
        if config.position_weight_factor < 0 or config.position_weight_factor > 1:
            raise SummarizerInvalidParameterError(
                "position_weight_factor must be between 0 and 1"
            )
        if config.exponential_decay_rate <= 0:
            raise SummarizerInvalidParameterError(
                "exponential_decay_rate must be positive"
            )

    def summarize(self, text: str, num_sentences: Optional[int] = None) -> list[str]:
        if text is None:
            raise SummarizerInvalidInputError("text cannot be None")

        n = num_sentences if num_sentences is not None else self._config.num_sentences
        if n < 0:
            raise SummarizerInvalidParameterError(
                "num_sentences must be non-negative"
            )
        if n == 0:
            return []

        sentences = _split_sentences(text)
        if not sentences:
            return []

        if len(sentences) <= n:
            return list(sentences)

        scored_sentences = self._score_sentences(sentences)
        selected = self._select_with_redundancy_penalty(scored_sentences, n)

        selected.sort(key=lambda s: s.index)
        return [s.text for s in selected]

    def summarize_with_scores(
        self, text: str, num_sentences: Optional[int] = None
    ) -> list[SentenceScore]:
        if text is None:
            raise SummarizerInvalidInputError("text cannot be None")

        n = num_sentences if num_sentences is not None else self._config.num_sentences
        if n < 0:
            raise SummarizerInvalidParameterError(
                "num_sentences must be non-negative"
            )
        if n == 0:
            return []

        sentences = _split_sentences(text)
        if not sentences:
            return []

        if len(sentences) <= n:
            return self._score_sentences(sentences)

        scored_sentences = self._score_sentences(sentences)
        selected = self._select_with_redundancy_penalty(scored_sentences, n)
        selected.sort(key=lambda s: s.index)
        return selected

    def _score_sentences(self, sentences: list[str]) -> list[SentenceScore]:
        all_tokens: list[list[str]] = []
        word_counter: Counter[str] = Counter()

        for sentence in sentences:
            terms = self._tokenizer.tokenize_terms(sentence)
            filtered = self._stopwords.filter(terms)
            all_tokens.append(filtered)
            word_counter.update(filtered)

        total_words = sum(word_counter.values())
        if total_words == 0:
            result: list[SentenceScore] = []
            for i, sentence in enumerate(sentences):
                pos_weight = _compute_position_weight(
                    i,
                    len(sentences),
                    self._config.position_decay,
                    self._config.exponential_decay_rate,
                    self._config.position_weight_factor,
                )
                result.append(
                    SentenceScore(
                        index=i,
                        text=sentence,
                        frequency_score=0.0,
                        position_weight=pos_weight,
                        final_score=0.0 * pos_weight,
                        tokens=[],
                    )
                )
            return result

        scored: list[SentenceScore] = []
        for i, (sentence, tokens) in enumerate(zip(sentences, all_tokens)):
            if not tokens:
                freq_score = 0.0
            else:
                freq_sum = sum(word_counter[t] for t in tokens)
                freq_score = freq_sum / len(tokens)

            pos_weight = _compute_position_weight(
                i,
                len(sentences),
                self._config.position_decay,
                self._config.exponential_decay_rate,
                self._config.position_weight_factor,
            )

            scored.append(
                SentenceScore(
                    index=i,
                    text=sentence,
                    frequency_score=freq_score,
                    position_weight=pos_weight,
                    final_score=freq_score * pos_weight,
                    tokens=tokens,
                )
            )

        return scored

    def _select_with_redundancy_penalty(
        self, scored_sentences: list[SentenceScore], n: int
    ) -> list[SentenceScore]:
        penalty_tracker: dict[int, float] = {s.index: 1.0 for s in scored_sentences}
        selected: list[SentenceScore] = []
        selected_tokens: list[set[str]] = []

        available = list(scored_sentences)

        while len(selected) < n and available:
            available.sort(
                key=lambda s: s.final_score * penalty_tracker[s.index],
                reverse=True,
            )

            best = available.pop(0)
            selected.append(best)
            selected_tokens.append(set(best.tokens))

            for candidate in available:
                candidate_tokens = set(candidate.tokens)
                max_sim = 0.0
                for sel_tokens in selected_tokens:
                    if self._config.similarity_metric == SimilarityMetric.JACCARD:
                        sim = _jaccard_similarity(candidate_tokens, sel_tokens)
                    else:
                        sim = _shared_ratio(candidate_tokens, sel_tokens)
                    if sim > max_sim:
                        max_sim = sim

                if max_sim >= self._config.similarity_threshold:
                    penalty_tracker[candidate.index] *= (
                        1.0 - self._config.redundancy_penalty
                    )

        return selected

    @property
    def config(self) -> SummarizerConfig:
        return SummarizerConfig(
            num_sentences=self._config.num_sentences,
            position_decay=self._config.position_decay,
            position_weight_factor=self._config.position_weight_factor,
            exponential_decay_rate=self._config.exponential_decay_rate,
            similarity_metric=self._config.similarity_metric,
            similarity_threshold=self._config.similarity_threshold,
            redundancy_penalty=self._config.redundancy_penalty,
            extra_stopwords=set(self._config.extra_stopwords)
            if self._config.extra_stopwords
            else None,
        )


def summarize_text(
    text: str,
    num_sentences: int = 3,
    position_decay: PositionDecayType = PositionDecayType.LINEAR,
    position_weight_factor: float = 1.0,
    exponential_decay_rate: float = 0.5,
    similarity_metric: SimilarityMetric = SimilarityMetric.JACCARD,
    similarity_threshold: float = 0.5,
    redundancy_penalty: float = 0.5,
    extra_stopwords: Optional[set[str]] = None,
) -> list[str]:
    config = SummarizerConfig(
        num_sentences=num_sentences,
        position_decay=position_decay,
        position_weight_factor=position_weight_factor,
        exponential_decay_rate=exponential_decay_rate,
        similarity_metric=similarity_metric,
        similarity_threshold=similarity_threshold,
        redundancy_penalty=redundancy_penalty,
        extra_stopwords=extra_stopwords,
    )
    summarizer = TextSummarizer(config)
    return summarizer.summarize(text, num_sentences)
