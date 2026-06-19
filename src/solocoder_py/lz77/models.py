from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .exceptions import InvalidConfigError


@dataclass
class CompressionStats:
    original_size: int
    compressed_size: int
    literal_count: int
    match_count: int
    hash_chain_truncations: int

    @property
    def compression_ratio(self) -> float:
        if self.original_size == 0:
            return 0.0
        return self.compressed_size / self.original_size

    @property
    def savings_ratio(self) -> float:
        if self.original_size == 0:
            return 0.0
        return 1.0 - self.compressed_size / self.original_size


@dataclass
class MatchResult:
    distance: int
    length: int
    found: bool


class LZ77Config:
    DEFAULT_WINDOW_SIZE = 32768
    DEFAULT_MIN_MATCH_LENGTH = 3
    DEFAULT_MAX_MATCH_LENGTH = 258
    DEFAULT_HASH_CHAIN_LIMIT = 256
    DEFAULT_LITERAL_BLOCK_MAX = 128

    def __init__(
        self,
        window_size: int = DEFAULT_WINDOW_SIZE,
        min_match_length: int = DEFAULT_MIN_MATCH_LENGTH,
        max_match_length: int = DEFAULT_MAX_MATCH_LENGTH,
        hash_chain_limit: int = DEFAULT_HASH_CHAIN_LIMIT,
        literal_block_max: int = DEFAULT_LITERAL_BLOCK_MAX,
    ) -> None:
        if window_size < 1:
            raise InvalidConfigError(f"window_size must be >= 1, got {window_size}")
        if min_match_length < 2:
            raise InvalidConfigError(
                f"min_match_length must be >= 2, got {min_match_length}"
            )
        if max_match_length < min_match_length:
            raise InvalidConfigError(
                f"max_match_length must be >= min_match_length, "
                f"got {max_match_length} < {min_match_length}"
            )
        if hash_chain_limit < 1:
            raise InvalidConfigError(
                f"hash_chain_limit must be >= 1, got {hash_chain_limit}"
            )
        if literal_block_max < 1:
            raise InvalidConfigError(
                f"literal_block_max must be >= 1, got {literal_block_max}"
            )

        self._window_size = window_size
        self._min_match_length = min_match_length
        self._max_match_length = max_match_length
        self._hash_chain_limit = hash_chain_limit
        self._literal_block_max = literal_block_max

    @property
    def window_size(self) -> int:
        return self._window_size

    @property
    def min_match_length(self) -> int:
        return self._min_match_length

    @property
    def max_match_length(self) -> int:
        return self._max_match_length

    @property
    def hash_chain_limit(self) -> int:
        return self._hash_chain_limit

    @property
    def literal_block_max(self) -> int:
        return self._literal_block_max
