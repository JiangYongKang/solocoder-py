from __future__ import annotations

import hashlib
import hmac
import os
from abc import ABC, abstractmethod
from typing import Dict, Type

from .exceptions import AlgorithmNotFoundError
from .models import AlgorithmVersion


class HashAlgorithm(ABC):
    version: AlgorithmVersion
    name: str
    max_iterations: int = 2**31

    @abstractmethod
    def hash(self, data: bytes, salt: bytes, iterations: int) -> bytes:
        pass


class SHA256Algorithm(HashAlgorithm):
    version = AlgorithmVersion.SHA256_V1
    name = "SHA-256"

    def hash(self, data: bytes, salt: bytes, iterations: int) -> bytes:
        result = salt + data
        for _ in range(max(1, iterations)):
            result = hashlib.sha256(result).digest()
        return result


class SHA512Algorithm(HashAlgorithm):
    version = AlgorithmVersion.SHA512_V2
    name = "SHA-512"

    def hash(self, data: bytes, salt: bytes, iterations: int) -> bytes:
        result = salt + data
        for _ in range(max(1, iterations)):
            result = hashlib.sha512(result).digest()
        return result


class BcryptSimulatedAlgorithm(HashAlgorithm):
    version = AlgorithmVersion.BCRYPT_V3
    name = "Bcrypt-Simulated"
    max_iterations = 31

    def hash(self, data: bytes, salt: bytes, iterations: int) -> bytes:
        cost = max(1, iterations)
        pepper = b"bcrypt_simulated_pepper_v3"
        combined = salt + data
        for i in range(cost):
            combined = hmac.new(pepper + i.to_bytes(4, "big"), combined, hashlib.sha512).digest()
        return combined


ALGORITHM_REGISTRY: Dict[AlgorithmVersion, HashAlgorithm] = {}


def register_algorithm(algorithm_cls: Type[HashAlgorithm]) -> None:
    ALGORITHM_REGISTRY[algorithm_cls.version] = algorithm_cls()


def get_algorithm(version: AlgorithmVersion) -> HashAlgorithm:
    if version not in ALGORITHM_REGISTRY:
        raise AlgorithmNotFoundError(f"Algorithm {version} not found")
    return ALGORITHM_REGISTRY[version]


def generate_salt(length: int) -> bytes:
    if length <= 0:
        return b""
    return os.urandom(length)


def constant_time_compare(a: bytes, b: bytes) -> bool:
    result = len(a) ^ len(b)
    for i in range(max(len(a), len(b))):
        val_a = a[i] if i < len(a) else 0
        val_b = b[i] if i < len(b) else 0
        result |= val_a ^ val_b
    return result == 0


register_algorithm(SHA256Algorithm)
register_algorithm(SHA512Algorithm)
register_algorithm(BcryptSimulatedAlgorithm)
