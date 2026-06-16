from __future__ import annotations

import hashlib
import struct
from typing import Callable

from .exceptions import InvalidConfigError


def ngram_tokens(text: str, n: int = 3) -> set[str]:
    if not isinstance(text, str):
        text = str(text)
    if n <= 0:
        raise InvalidConfigError("n must be a positive integer")
    if len(text) < n:
        return {text} if text else set()
    return {text[i : i + n] for i in range(len(text) - n + 1)}


def _make_hash_fn(seed: int) -> Callable[[str], int]:
    def hash_fn(token: str) -> int:
        h = hashlib.sha256()
        h.update(struct.pack("<I", seed))
        h.update(token.encode("utf-8"))
        digest = h.digest()
        return struct.unpack("<Q", digest[:8])[0]

    return hash_fn


class MinHash:
    def __init__(
        self,
        num_perm: int = 128,
        n: int = 3,
        seed: int = 42,
    ) -> None:
        if num_perm <= 0:
            raise InvalidConfigError("num_perm must be a positive integer")
        if n <= 0:
            raise InvalidConfigError("n must be a positive integer")
        self.num_perm = num_perm
        self.n = n
        self.seed = seed
        self._hash_fns: list[Callable[[str], int]] = [
            _make_hash_fn(seed + i) for i in range(num_perm)
        ]

    def compute_signature(self, text: str) -> list[int]:
        tokens = ngram_tokens(text, self.n)
        if not tokens:
            return [0] * self.num_perm

        signature: list[int] = []
        for hash_fn in self._hash_fns:
            min_hash = min(hash_fn(token) for token in tokens)
            signature.append(min_hash)
        return signature

    def compute_signature_from_tokens(self, tokens: set[str]) -> list[int]:
        if not tokens:
            return [0] * self.num_perm

        signature: list[int] = []
        for hash_fn in self._hash_fns:
            min_hash = min(hash_fn(token) for token in tokens)
            signature.append(min_hash)
        return signature

    @staticmethod
    def jaccard_from_signatures(sig_a: list[int], sig_b: list[int]) -> float:
        if len(sig_a) != len(sig_b):
            raise ValueError("signatures must have the same length")
        if not sig_a:
            return 0.0
        matches = sum(1 for a, b in zip(sig_a, sig_b) if a == b)
        return matches / len(sig_a)


def jaccard_similarity(set_a: set[str], set_b: set[str]) -> float:
    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    if union == 0:
        return 0.0
    return intersection / union
