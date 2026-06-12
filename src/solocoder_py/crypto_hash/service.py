from __future__ import annotations

from typing import Optional

from .algorithms import constant_time_compare, generate_salt, get_algorithm
from .exceptions import (
    AlgorithmNotFoundError,
    HashVerificationError,
    InvalidHashFormatError,
    InvalidSaltError,
    SaltTamperedError,
)
from .models import (
    AlgorithmVersion,
    HashParameters,
    HashResult,
    RehashStatus,
    VerificationResult,
)
from .store import InMemoryHashStore


ALGORITHM_VERSION_ORDER = [
    AlgorithmVersion.SHA256_V1,
    AlgorithmVersion.SHA512_V2,
    AlgorithmVersion.BCRYPT_V3,
]


def get_algorithm_version_index(version: AlgorithmVersion) -> int:
    try:
        return ALGORITHM_VERSION_ORDER.index(version)
    except ValueError:
        raise AlgorithmNotFoundError(f"Algorithm {version} not in version order")


def is_newer_version(current: AlgorithmVersion, stored: AlgorithmVersion) -> bool:
    return get_algorithm_version_index(current) > get_algorithm_version_index(stored)


class CryptoHashService:
    def __init__(
        self,
        default_algorithm: AlgorithmVersion = AlgorithmVersion.BCRYPT_V3,
        salt_length: int = 16,
        iterations: int = 10,
        store: Optional[InMemoryHashStore] = None,
    ) -> None:
        if salt_length < 0:
            raise InvalidSaltError("Salt length cannot be negative")
        if iterations < 1:
            raise ValueError("Iterations must be at least 1")

        self.default_algorithm = default_algorithm
        self.default_salt_length = salt_length
        self.default_iterations = iterations
        self.store = store or InMemoryHashStore()

    def get_current_parameters(self) -> HashParameters:
        return HashParameters(
            algorithm_version=self.default_algorithm,
            salt_length=self.default_salt_length,
            iterations=self.default_iterations,
        )

    def hash(
        self,
        data: bytes,
        salt: Optional[bytes] = None,
        algorithm_version: Optional[AlgorithmVersion] = None,
        salt_length: Optional[int] = None,
        iterations: Optional[int] = None,
    ) -> HashResult:
        algo_version = algorithm_version if algorithm_version is not None else self.default_algorithm
        effective_salt_length = salt_length if salt_length is not None else self.default_salt_length
        effective_iterations = iterations if iterations is not None else self.default_iterations

        if effective_salt_length < 0:
            raise InvalidSaltError("Salt length cannot be negative")
        if effective_iterations < 1:
            raise ValueError("Iterations must be at least 1")

        if salt is None:
            salt = generate_salt(effective_salt_length)
        else:
            if len(salt) != effective_salt_length and effective_salt_length > 0:
                raise InvalidSaltError(
                    f"Provided salt length {len(salt)} does not match expected {effective_salt_length}"
                )

        algorithm = get_algorithm(algo_version)
        effective_iterations = min(effective_iterations, algorithm.max_iterations)
        hash_value = algorithm.hash(data, salt, effective_iterations)

        return HashResult(
            algorithm_version=algo_version,
            salt=salt,
            hash_value=hash_value,
            salt_length=effective_salt_length,
            iterations=effective_iterations,
        )

    def verify(
        self,
        data: bytes,
        stored_hash: HashResult,
        auto_migrate: bool = True,
    ) -> VerificationResult:
        try:
            algorithm = get_algorithm(stored_hash.algorithm_version)
        except AlgorithmNotFoundError:
            raise

        if len(stored_hash.salt) != stored_hash.salt_length and stored_hash.salt_length > 0:
            raise SaltTamperedError(
                f"Stored salt length {len(stored_hash.salt)} does not match recorded {stored_hash.salt_length}"
            )

        clamped_iterations = min(stored_hash.iterations, algorithm.max_iterations)
        computed_hash = algorithm.hash(
            data, stored_hash.salt, clamped_iterations
        )
        matches = constant_time_compare(computed_hash, stored_hash.hash_value)

        if not matches:
            return VerificationResult(
                success=False,
                rehash_result=None,
                rehash_needed=False,
            )

        rehash_status = self.check_rehash_needed(stored_hash)
        rehash_needed = rehash_status.needs_rehash
        rehash_result = None

        if auto_migrate and rehash_needed:
            rehash_result = self.hash(
                data,
                algorithm_version=self.default_algorithm,
                salt_length=self.default_salt_length,
                iterations=self.default_iterations,
            )

        return VerificationResult(
            success=True,
            rehash_result=rehash_result,
            rehash_needed=rehash_needed,
        )

    def verify_and_update(
        self,
        username: str,
        data: bytes,
        auto_migrate: bool = True,
    ) -> VerificationResult:
        credentials = self.store.get_user_credentials(username)
        if credentials is None:
            raise HashVerificationError(f"User {username} not found")

        stored_hash = credentials.stored_hash
        result = self.verify(data, stored_hash, auto_migrate)

        if result.success and auto_migrate and result.rehash_result is not None:
            self.store.update_user_credentials(username, result.rehash_result)

        return result

    def check_rehash_needed(self, stored_hash: HashResult) -> RehashStatus:
        reasons: list[str] = []

        if is_newer_version(self.default_algorithm, stored_hash.algorithm_version):
            reasons.append(
                f"Algorithm is outdated: {stored_hash.algorithm_version.value} -> {self.default_algorithm.value}"
            )

        if stored_hash.salt_length != self.default_salt_length:
            reasons.append(
                f"Salt length changed: {stored_hash.salt_length} -> {self.default_salt_length}"
            )

        default_algo = get_algorithm(self.default_algorithm)
        effective_default_iterations = min(self.default_iterations, default_algo.max_iterations)

        if stored_hash.algorithm_version == self.default_algorithm:
            if stored_hash.iterations != effective_default_iterations:
                reasons.append(
                    f"Iterations changed: {stored_hash.iterations} -> {effective_default_iterations}"
                )
        else:
            stored_algo = get_algorithm(stored_hash.algorithm_version)
            effective_stored_iterations = min(stored_hash.iterations, stored_algo.max_iterations)
            if effective_stored_iterations != effective_default_iterations:
                reasons.append(
                    f"Iterations changed: {effective_stored_iterations} -> {effective_default_iterations}"
                )

        return RehashStatus(
            needs_rehash=len(reasons) > 0,
            reasons=reasons,
        )