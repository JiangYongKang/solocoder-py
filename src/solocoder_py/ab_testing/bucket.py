from __future__ import annotations

import hashlib


BUCKET_COUNT = 100


class StableHashBucketer:
    @staticmethod
    def _hash(key: str) -> int:
        digest = hashlib.sha256(key.encode("utf-8")).digest()
        return int.from_bytes(digest[:4], byteorder="big", signed=False)

    @classmethod
    def get_global_bucket(cls, user_id: str) -> int:
        return cls._hash(user_id) % BUCKET_COUNT

    @classmethod
    def get_within_group_bucket(cls, user_id: str, group_bucket_count: int) -> int:
        salted_key = f"mutex_group::{user_id}"
        return cls._hash(salted_key) % group_bucket_count
