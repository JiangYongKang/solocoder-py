from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class AlgorithmVersion(str, Enum):
    SHA256_V1 = "sha256_v1"
    SHA512_V2 = "sha512_v2"
    BCRYPT_V3 = "bcrypt_v3"


@dataclass
class HashParameters:
    algorithm_version: AlgorithmVersion
    salt_length: int
    iterations: int


@dataclass
class HashResult:
    algorithm_version: AlgorithmVersion
    salt: bytes
    hash_value: bytes
    salt_length: int
    iterations: int

    def serialize(self) -> bytes:
        parts = [
            self.algorithm_version.value.encode("utf-8"),
            self.salt,
            self.hash_value,
            self.salt_length.to_bytes(4, "big"),
            self.iterations.to_bytes(4, "big"),
        ]
        data = b"$".join([p.hex().encode("utf-8") for p in parts])
        return data

    @classmethod
    def deserialize(cls, data: bytes) -> "HashResult":
        from .exceptions import InvalidHashFormatError

        try:
            parts_hex = data.decode("utf-8").split("$")
            if len(parts_hex) != 5:
                raise InvalidHashFormatError("Hash result must contain exactly 5 parts")
            parts = [bytes.fromhex(p) for p in parts_hex]
            algorithm_version = AlgorithmVersion(parts[0].decode("utf-8"))
            salt = parts[1]
            hash_value = parts[2]
            salt_length = int.from_bytes(parts[3], "big")
            iterations = int.from_bytes(parts[4], "big")
            return cls(
                algorithm_version=algorithm_version,
                salt=salt,
                hash_value=hash_value,
                salt_length=salt_length,
                iterations=iterations,
            )
        except (ValueError, UnicodeDecodeError, KeyError) as e:
            raise InvalidHashFormatError(f"Invalid hash format: {e}") from e


@dataclass
class RehashStatus:
    needs_rehash: bool
    reasons: list[str] = field(default_factory=list)


@dataclass
class VerificationResult:
    success: bool
    rehash_result: Optional[HashResult] = None
    rehash_needed: bool = False
