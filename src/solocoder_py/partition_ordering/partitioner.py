from __future__ import annotations

import hashlib
from typing import Optional


class Partitioner:
    def __init__(self, num_partitions: int) -> None:
        if num_partitions <= 0:
            raise ValueError("num_partitions must be positive")
        self._num_partitions = num_partitions

    @property
    def num_partitions(self) -> int:
        return self._num_partitions

    def partition(self, key: str) -> int:
        if key is None:
            raise ValueError("key must not be None")
        digest = hashlib.md5(key.encode("utf-8")).digest()
        hash_val = int.from_bytes(digest[:4], byteorder="big", signed=False)
        return hash_val % self._num_partitions

    def partition_stable(self, key: str) -> int:
        return self.partition(key)
