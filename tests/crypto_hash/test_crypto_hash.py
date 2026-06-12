from __future__ import annotations

import time
from typing import Type

import pytest

from solocoder_py.crypto_hash import (
    AlgorithmNotFoundError,
    AlgorithmVersion,
    BcryptSimulatedAlgorithm,
    CryptoHashError,
    CryptoHashService,
    HashAlgorithm,
    HashResult,
    InMemoryHashStore,
    InvalidHashFormatError,
    InvalidSaltError,
    SHA256Algorithm,
    SHA512Algorithm,
    SaltTamperedError,
    HashVerificationError,
    constant_time_compare,
    generate_salt,
    get_algorithm,
    is_newer_version,
    register_algorithm,
)


class TestSaltedHash:
    def test_salted_hash_generates_different_salts(self, make_service):
        service = make_service()
        data = b"my_password_123"

        result1 = service.hash(data)
        result2 = service.hash(data)

        assert result1.salt != result2.salt
        assert result1.hash_value != result2.hash_value
        assert len(result1.salt) == service.default_salt_length
        assert len(result2.salt) == service.default_salt_length

    def test_salted_hash_verification_consistency(self, make_service):
        service = make_service()
        data = b"my_password_123"

        result = service.hash(data)
        verification = service.verify(data, result)

        assert verification.success is True
        assert verification.rehash_needed is False
        assert verification.rehash_result is None

    def test_salted_hash_wrong_data_fails(self, make_service):
        service = make_service()
        data = b"my_password_123"
        wrong_data = b"wrong_password"

        result = service.hash(data)
        verification = service.verify(wrong_data, result)

        assert verification.success is False
        assert verification.rehash_needed is False
        assert verification.rehash_result is None

    def test_salt_stored_with_hash(self, make_service):
        service = make_service()
        data = b"test_data"

        result = service.hash(data)

        assert result.salt is not None
        assert result.salt_length == service.default_salt_length
        assert len(result.salt) == result.salt_length

    def test_custom_salt(self, make_service):
        service = make_service()
        data = b"test_data"
        custom_salt = b"\x00" * 16

        result = service.hash(data, salt=custom_salt)

        assert result.salt == custom_salt

    def test_custom_salt_wrong_length_raises(self, make_service):
        service = make_service()
        data = b"test_data"
        wrong_salt = b"\x00" * 8

        with pytest.raises(InvalidSaltError):
            service.hash(data, salt=wrong_salt)


class TestAlgorithmMigration:
    def test_algorithm_migration_old_hash_verifies_and_rehashes(self, make_service):
        old_service = make_service(algorithm=AlgorithmVersion.SHA256_V1)
        new_service = make_service(algorithm=AlgorithmVersion.BCRYPT_V3)
        data = b"password123"

        old_hash = old_service.hash(data)
        assert old_hash.algorithm_version == AlgorithmVersion.SHA256_V1

        verification = new_service.verify(data, old_hash, auto_migrate=True)

        assert verification.success is True
        assert verification.rehash_needed is True
        assert verification.rehash_result is not None
        assert verification.rehash_result.algorithm_version == AlgorithmVersion.BCRYPT_V3

        re_verification = new_service.verify(data, verification.rehash_result)
        assert re_verification.success is True
        assert re_verification.rehash_needed is False

    def test_algorithm_migration_chain_multiple_upgrades(self, make_service):
        data = b"chain_password"

        v1_service = make_service(algorithm=AlgorithmVersion.SHA256_V1)
        v2_service = make_service(algorithm=AlgorithmVersion.SHA512_V2)
        v3_service = make_service(algorithm=AlgorithmVersion.BCRYPT_V3)

        v1_hash = v1_service.hash(data)
        assert v1_hash.algorithm_version == AlgorithmVersion.SHA256_V1

        v2_result = v2_service.verify(data, v1_hash, auto_migrate=True)
        assert v2_result.success is True
        assert v2_result.rehash_result is not None
        assert v2_result.rehash_result.algorithm_version == AlgorithmVersion.SHA512_V2

        v3_result = v3_service.verify(data, v2_result.rehash_result, auto_migrate=True)
        assert v3_result.success is True
        assert v3_result.rehash_result is not None
        assert v3_result.rehash_result.algorithm_version == AlgorithmVersion.BCRYPT_V3

        final_verify = v3_service.verify(data, v3_result.rehash_result)
        assert final_verify.success is True
        assert final_verify.rehash_needed is False

    def test_verify_and_update_store(self, make_service, make_store):
        store = make_store()
        service = make_service(algorithm=AlgorithmVersion.BCRYPT_V3)
        service.store = store

        old_service = make_service(algorithm=AlgorithmVersion.SHA256_V1)
        old_service.store = store

        username = "test_user"
        password = b"user_password"

        old_hash = old_service.hash(password)
        store.store_user_credentials(username, old_hash)

        result = service.verify_and_update(username, password)

        assert result.success is True
        assert result.rehash_needed is True
        assert result.rehash_result is not None
        assert result.rehash_result.algorithm_version == AlgorithmVersion.BCRYPT_V3

        updated = store.get_user_credentials(username)
        assert updated is not None
        assert updated.stored_hash.algorithm_version == AlgorithmVersion.BCRYPT_V3

    def test_migration_without_auto_migrate_flag(self, make_service):
        old_service = make_service(algorithm=AlgorithmVersion.SHA256_V1)
        new_service = make_service(algorithm=AlgorithmVersion.BCRYPT_V3)
        data = b"password123"

        old_hash = old_service.hash(data)
        verification = new_service.verify(data, old_hash, auto_migrate=False)

        assert verification.success is True
        assert verification.rehash_needed is True
        assert verification.rehash_result is None

    def test_old_algorithm_remains_available(self, make_service):
        for version in AlgorithmVersion:
            algorithm = get_algorithm(version)
            assert algorithm is not None
            assert algorithm.version == version

    def test_single_algorithm_cannot_downgrade(self):
        original_registry = dict(__import__('solocoder_py.crypto_hash.algorithms', fromlist=['ALGORITHM_REGISTRY']).ALGORITHM_REGISTRY)
        original_order = list(__import__('solocoder_py.crypto_hash.service', fromlist=['ALGORITHM_VERSION_ORDER']).ALGORITHM_VERSION_ORDER)

        try:
            import solocoder_py.crypto_hash.algorithms as alg_module
            import solocoder_py.crypto_hash.service as service_module

            alg_module.ALGORITHM_REGISTRY.clear()
            service_module.ALGORITHM_VERSION_ORDER.clear()
            service_module.ALGORITHM_VERSION_ORDER.append(AlgorithmVersion.BCRYPT_V3)

            class OnlyAlgorithm(HashAlgorithm):
                version = AlgorithmVersion.BCRYPT_V3
                name = "Only-Algo"

                def hash(self, data: bytes, salt: bytes, iterations: int) -> bytes:
                    return data + salt

            register_algorithm(OnlyAlgorithm)

            service = CryptoHashService(
                default_algorithm=AlgorithmVersion.BCRYPT_V3,
                salt_length=16,
                iterations=10,
            )

            data = b"test"
            hash_result = service.hash(data)
            status = service.check_rehash_needed(hash_result)

            assert status.needs_rehash is False
            assert len(status.reasons) == 0

        finally:
            import solocoder_py.crypto_hash.algorithms as alg_module
            import solocoder_py.crypto_hash.service as service_module

            alg_module.ALGORITHM_REGISTRY.clear()
            service_module.ALGORITHM_VERSION_ORDER.clear()
            service_module.ALGORITHM_VERSION_ORDER.extend(original_order)

            register_algorithm(SHA256Algorithm)
            register_algorithm(SHA512Algorithm)
            register_algorithm(BcryptSimulatedAlgorithm)


class TestRehashDetection:
    def test_rehash_detection_outdated_algorithm(self, make_service):
        old_service = make_service(algorithm=AlgorithmVersion.SHA256_V1)
        new_service = make_service(algorithm=AlgorithmVersion.BCRYPT_V3)

        old_hash = old_service.hash(b"test")
        status = new_service.check_rehash_needed(old_hash)

        assert status.needs_rehash is True
        assert any("Algorithm is outdated" in r for r in status.reasons)

    def test_rehash_detection_salt_length_changed(self, make_service):
        short_service = make_service(salt_length=8)
        long_service = make_service(salt_length=32)

        short_hash = short_service.hash(b"test")
        status = long_service.check_rehash_needed(short_hash)

        assert status.needs_rehash is True
        assert any("Salt length changed" in r for r in status.reasons)

    def test_rehash_detection_iterations_changed(self, make_service):
        low_service = make_service(iterations=1)
        high_service = make_service(iterations=100)

        low_hash = low_service.hash(b"test")
        status = high_service.check_rehash_needed(low_hash)

        assert status.needs_rehash is True
        assert any("Iterations changed" in r for r in status.reasons)

    def test_rehash_detection_no_changes_needed(self, make_service):
        service = make_service()
        hash_result = service.hash(b"test")
        status = service.check_rehash_needed(hash_result)

        assert status.needs_rehash is False
        assert len(status.reasons) == 0

    def test_rehash_detection_multiple_changes(self):
        old_service = CryptoHashService(
            default_algorithm=AlgorithmVersion.SHA256_V1,
            salt_length=8,
            iterations=1,
        )
        new_service = CryptoHashService(
            default_algorithm=AlgorithmVersion.BCRYPT_V3,
            salt_length=32,
            iterations=100,
        )

        old_hash = old_service.hash(b"test")
        status = new_service.check_rehash_needed(old_hash)

        assert status.needs_rehash is True
        assert len(status.reasons) == 3

    def test_algorithm_version_equal(self):
        assert is_newer_version(AlgorithmVersion.SHA256_V1, AlgorithmVersion.SHA256_V1) is False
        assert is_newer_version(AlgorithmVersion.SHA512_V2, AlgorithmVersion.SHA512_V2) is False

    def test_algorithm_version_comparison(self):
        assert is_newer_version(AlgorithmVersion.SHA512_V2, AlgorithmVersion.SHA256_V1) is True
        assert is_newer_version(AlgorithmVersion.BCRYPT_V3, AlgorithmVersion.SHA512_V2) is True
        assert is_newer_version(AlgorithmVersion.SHA256_V1, AlgorithmVersion.BCRYPT_V3) is False


class TestConstantTimeCompare:
    def test_constant_time_compare_equal(self):
        a = b"\x01\x02\x03\x04"
        b = b"\x01\x02\x03\x04"

        assert constant_time_compare(a, b) is True

    def test_constant_time_compare_not_equal(self):
        a = b"\x01\x02\x03\x04"
        b = b"\x01\x02\x03\x05"

        assert constant_time_compare(a, b) is False

    def test_constant_time_compare_different_lengths(self):
        a = b"\x01\x02\x03"
        b = b"\x01\x02\x03\x04"

        assert constant_time_compare(a, b) is False

    def test_constant_time_compare_empty_equal(self):
        assert constant_time_compare(b"", b"") is True

    def test_constant_time_compare_empty_not_equal(self):
        assert constant_time_compare(b"", b"\x01") is False

    def test_constant_time_compare_long_strings(self):
        a = b"a" * 10000
        b = b"a" * 10000
        c = b"a" * 9999 + b"b"

        assert constant_time_compare(a, b) is True
        assert constant_time_compare(a, c) is False

    def test_constant_time_compare_timing(self):
        a = b"\x00" * 10000
        b = b"\x00" * 10000
        c = b"\x01" + b"\x00" * 9999
        d = b"\x00" * 9999 + b"\x01"

        def measure(data1, data2, iterations=100):
            start = time.perf_counter()
            for _ in range(iterations):
                constant_time_compare(data1, data2)
            return time.perf_counter() - start

        time_equal = measure(a, b)
        time_diff_start = measure(a, c)
        time_diff_end = measure(a, d)

        ratio_start_end = abs(time_diff_start - time_diff_end) / max(time_diff_start, time_diff_end)
        ratio_equal_diff = abs(time_equal - time_diff_end) / max(time_equal, time_diff_end)

        assert ratio_start_end < 0.5, f"Timing difference too large: {ratio_start_end}"
        assert ratio_equal_diff < 0.5, f"Timing difference between equal and diff too large: {ratio_equal_diff}"


class TestBoundaryConditions:
    def test_empty_string_input(self, make_service):
        service = make_service()
        empty_data = b""

        result = service.hash(empty_data)
        verification = service.verify(empty_data, result)

        assert verification.success is True
        assert len(result.salt) == service.default_salt_length

    def test_empty_string_vs_non_empty(self, make_service):
        service = make_service()
        empty_data = b""
        non_empty_data = b"\x00"

        result_empty = service.hash(empty_data)
        result_non_empty = service.hash(non_empty_data)

        assert service.verify(empty_data, result_empty).success is True
        assert service.verify(non_empty_data, result_non_empty).success is True
        assert service.verify(non_empty_data, result_empty).success is False
        assert service.verify(empty_data, result_non_empty).success is False

    def test_extremely_long_input(self, make_service):
        service = make_service()
        long_data = b"x" * 1000000

        result = service.hash(long_data)
        verification = service.verify(long_data, result)

        assert verification.success is True

    def test_zero_salt_length(self):
        service = CryptoHashService(
            default_algorithm=AlgorithmVersion.SHA256_V1,
            salt_length=0,
            iterations=1,
        )

        data = b"test"
        result = service.hash(data)

        assert result.salt == b""
        assert result.salt_length == 0

        verification = service.verify(data, result)
        assert verification.success is True

    def test_zero_salt_length_custom_salt(self):
        service = CryptoHashService(
            default_algorithm=AlgorithmVersion.SHA256_V1,
            salt_length=0,
            iterations=1,
        )

        data = b"test"
        result = service.hash(data, salt=b"")

        assert result.salt == b""
        assert service.verify(data, result).success is True

    def test_algorithm_version_boundaries(self):
        versions = list(AlgorithmVersion)

        for i, v1 in enumerate(versions):
            for j, v2 in enumerate(versions):
                if i < j:
                    assert is_newer_version(v2, v1) is True
                elif i > j:
                    assert is_newer_version(v2, v1) is False
                else:
                    assert is_newer_version(v2, v1) is False


class TestExceptionCases:
    def test_algorithm_not_found_error(self):
        original_registry = __import__('solocoder_py.crypto_hash.algorithms', fromlist=['ALGORITHM_REGISTRY']).ALGORITHM_REGISTRY.copy()

        try:
            import solocoder_py.crypto_hash.algorithms as alg_module
            alg_module.ALGORITHM_REGISTRY.clear()

            with pytest.raises(AlgorithmNotFoundError):
                get_algorithm(AlgorithmVersion.SHA256_V1)

        finally:
            import solocoder_py.crypto_hash.algorithms as alg_module
            alg_module.ALGORITHM_REGISTRY.clear()
            alg_module.ALGORITHM_REGISTRY.update(original_registry)

    def test_invalid_hash_format_missing_parts(self):
        invalid_data = b"only$three$parts"

        with pytest.raises(InvalidHashFormatError):
            HashResult.deserialize(invalid_data)

    def test_invalid_hash_format_corrupted_algorithm(self):
        service = CryptoHashService(
            default_algorithm=AlgorithmVersion.SHA256_V1,
            salt_length=4,
            iterations=1,
        )
        result = service.hash(b"test")
        serialized = result.serialize()

        parts = serialized.decode("utf-8").split("$")
        parts[0] = "invalid_algorithm".encode("utf-8").hex()
        corrupted = b"$".join([p.encode("utf-8") for p in parts])

        with pytest.raises(InvalidHashFormatError):
            HashResult.deserialize(corrupted)

    def test_invalid_hash_format_non_hex(self):
        invalid_data = b"not$hex$data$here$now"

        with pytest.raises(InvalidHashFormatError):
            HashResult.deserialize(invalid_data)

    def test_salt_tampered_verification_fails(self, make_service):
        service = make_service()
        data = b"test_password"
        result = service.hash(data)

        tampered_salt = bytes([b ^ 0xFF for b in result.salt])
        tampered_hash = HashResult(
            algorithm_version=result.algorithm_version,
            salt=tampered_salt,
            hash_value=result.hash_value,
            salt_length=result.salt_length,
            iterations=result.iterations,
        )

        verification = service.verify(data, tampered_hash)
        assert verification.success is False
        assert verification.rehash_needed is False
        assert verification.rehash_result is None

    def test_salt_length_tampered(self, make_service):
        service = make_service()
        data = b"test_password"
        result = service.hash(data)

        tampered_hash = HashResult(
            algorithm_version=result.algorithm_version,
            salt=result.salt,
            hash_value=result.hash_value,
            salt_length=result.salt_length + 1,
            iterations=result.iterations,
        )

        with pytest.raises(SaltTamperedError):
            service.verify(data, tampered_hash)

    def test_constant_time_compare_different_lengths_returns_false(self):
        assert constant_time_compare(b"short", b"longer string") is False
        assert constant_time_compare(b"longer string", b"short") is False

    def test_user_not_found_in_verify_and_update(self, make_service, make_store):
        service = make_service()
        service.store = make_store()

        with pytest.raises(HashVerificationError, match="User nonexistent not found"):
            service.verify_and_update("nonexistent", b"password")

    def test_negative_salt_length_raises(self):
        with pytest.raises(InvalidSaltError, match="Salt length cannot be negative"):
            CryptoHashService(salt_length=-1)

    def test_zero_iterations_raises(self):
        with pytest.raises(ValueError, match="Iterations must be at least 1"):
            CryptoHashService(iterations=0)

    def test_negative_iterations_raises(self):
        with pytest.raises(ValueError, match="Iterations must be at least 1"):
            CryptoHashService(iterations=-1)

    def test_hash_with_negative_salt_length_raises(self, make_service):
        service = make_service()
        with pytest.raises(InvalidSaltError, match="Salt length cannot be negative"):
            service.hash(b"test", salt_length=-1)

    def test_hash_with_zero_iterations_raises(self, make_service):
        service = make_service()
        with pytest.raises(ValueError, match="Iterations must be at least 1"):
            service.hash(b"test", iterations=0)

    def test_verify_with_removed_algorithm_raises(self, make_service):
        original_registry = __import__('solocoder_py.crypto_hash.algorithms', fromlist=['ALGORITHM_REGISTRY']).ALGORITHM_REGISTRY.copy()

        try:
            service = make_service(algorithm=AlgorithmVersion.SHA256_V1)
            data = b"test"
            hash_result = service.hash(data)

            import solocoder_py.crypto_hash.algorithms as alg_module
            del alg_module.ALGORITHM_REGISTRY[AlgorithmVersion.SHA256_V1]

            with pytest.raises(AlgorithmNotFoundError):
                service.verify(data, hash_result)

        finally:
            import solocoder_py.crypto_hash.algorithms as alg_module
            alg_module.ALGORITHM_REGISTRY.clear()
            alg_module.ALGORITHM_REGISTRY.update(original_registry)


class TestHashResultSerialization:
    def test_serialize_deserialize_roundtrip(self, make_service):
        service = make_service()
        data = b"test_data"
        original = service.hash(data)

        serialized = original.serialize()
        deserialized = HashResult.deserialize(serialized)

        assert deserialized.algorithm_version == original.algorithm_version
        assert deserialized.salt == original.salt
        assert deserialized.hash_value == original.hash_value
        assert deserialized.salt_length == original.salt_length
        assert deserialized.iterations == original.iterations

    def test_serialized_format(self, make_service):
        service = make_service()
        result = service.hash(b"test")
        serialized = result.serialize()

        parts = serialized.decode("utf-8").split("$")
        assert len(parts) == 5

    def test_deserialize_verified(self, make_service):
        service = make_service()
        data = b"verify_me"
        original = service.hash(data)

        serialized = original.serialize()
        deserialized = HashResult.deserialize(serialized)

        verification = service.verify(data, deserialized)
        assert verification.success is True


class TestGenerateSalt:
    def test_generate_salt_positive_length(self):
        salt = generate_salt(16)
        assert len(salt) == 16
        assert isinstance(salt, bytes)

    def test_generate_salt_zero_length(self):
        salt = generate_salt(0)
        assert salt == b""

    def test_generate_salt_negative_length(self):
        salt = generate_salt(-1)
        assert salt == b""

    def test_generate_salt_randomness(self):
        salts = [generate_salt(16) for _ in range(100)]
        assert len(set(salts)) == 100


class TestInMemoryHashStore:
    def test_store_and_retrieve_hash(self, make_store):
        store = make_store()
        service = CryptoHashService(
            default_algorithm=AlgorithmVersion.SHA256_V1,
            salt_length=4,
            iterations=1,
        )
        hash_result = service.hash(b"test")

        store.store_hash("key1", hash_result)
        retrieved = store.get_hash("key1")

        assert retrieved is not None
        assert retrieved.algorithm_version == hash_result.algorithm_version
        assert retrieved.hash_value == hash_result.hash_value

    def test_get_nonexistent_hash(self, make_store):
        store = make_store()
        assert store.get_hash("nonexistent") is None

    def test_delete_hash(self, make_store):
        store = make_store()
        service = CryptoHashService(
            default_algorithm=AlgorithmVersion.SHA256_V1,
            salt_length=4,
            iterations=1,
        )
        hash_result = service.hash(b"test")

        store.store_hash("key1", hash_result)
        assert store.delete_hash("key1") is True
        assert store.get_hash("key1") is None
        assert store.delete_hash("key1") is False

    def test_store_and_retrieve_user_credentials(self, make_store):
        store = make_store()
        service = CryptoHashService(
            default_algorithm=AlgorithmVersion.SHA256_V1,
            salt_length=4,
            iterations=1,
        )
        hash_result = service.hash(b"password")

        store.store_user_credentials("user1", hash_result)
        credentials = store.get_user_credentials("user1")

        assert credentials is not None
        assert credentials.username == "user1"
        assert credentials.stored_hash.hash_value == hash_result.hash_value

    def test_update_user_credentials(self, make_store):
        store = make_store()
        service = CryptoHashService(
            default_algorithm=AlgorithmVersion.SHA256_V1,
            salt_length=4,
            iterations=1,
        )
        old_hash = service.hash(b"old_password")
        new_hash = service.hash(b"new_password")

        store.store_user_credentials("user1", old_hash)
        assert store.update_user_credentials("user1", new_hash) is True

        updated = store.get_user_credentials("user1")
        assert updated is not None
        assert updated.stored_hash.hash_value == new_hash.hash_value

    def test_update_nonexistent_user(self, make_store):
        store = make_store()
        service = CryptoHashService(
            default_algorithm=AlgorithmVersion.SHA256_V1,
            salt_length=4,
            iterations=1,
        )
        hash_result = service.hash(b"test")

        assert store.update_user_credentials("nonexistent", hash_result) is False

    def test_delete_user_credentials(self, make_store):
        store = make_store()
        service = CryptoHashService(
            default_algorithm=AlgorithmVersion.SHA256_V1,
            salt_length=4,
            iterations=1,
        )
        hash_result = service.hash(b"test")

        store.store_user_credentials("user1", hash_result)
        assert store.delete_user_credentials("user1") is True
        assert store.get_user_credentials("user1") is None
        assert store.delete_user_credentials("user1") is False

    def test_clear_store(self, make_store):
        store = make_store()
        service = CryptoHashService(
            default_algorithm=AlgorithmVersion.SHA256_V1,
            salt_length=4,
            iterations=1,
        )
        hash_result = service.hash(b"test")

        store.store_hash("key1", hash_result)
        store.store_user_credentials("user1", hash_result)

        assert len(store) == 2
        store.clear()
        assert len(store) == 0
        assert store.get_hash("key1") is None
        assert store.get_user_credentials("user1") is None

    def test_store_len(self, make_store):
        store = make_store()
        service = CryptoHashService(
            default_algorithm=AlgorithmVersion.SHA256_V1,
            salt_length=4,
            iterations=1,
        )
        hash_result = service.hash(b"test")

        assert len(store) == 0
        store.store_hash("key1", hash_result)
        assert len(store) == 1
        store.store_user_credentials("user1", hash_result)
        assert len(store) == 2


class TestCryptoHashService:
    def test_get_current_parameters(self, make_service):
        service = make_service(
            algorithm=AlgorithmVersion.SHA512_V2,
            salt_length=24,
            iterations=50,
        )

        params = service.get_current_parameters()

        assert params.algorithm_version == AlgorithmVersion.SHA512_V2
        assert params.salt_length == 24
        assert params.iterations == 50

    def test_custom_algorithm_in_hash(self, make_service):
        service = make_service(algorithm=AlgorithmVersion.BCRYPT_V3)
        data = b"test"

        sha256_result = service.hash(data, algorithm_version=AlgorithmVersion.SHA256_V1)
        assert sha256_result.algorithm_version == AlgorithmVersion.SHA256_V1

        bcrypt_result = service.hash(data, algorithm_version=AlgorithmVersion.BCRYPT_V3)
        assert bcrypt_result.algorithm_version == AlgorithmVersion.BCRYPT_V3

    def test_custom_parameters_in_hash(self, make_service):
        service = make_service(salt_length=16, iterations=10)
        data = b"test"

        custom_result = service.hash(
            data,
            salt_length=32,
            iterations=100,
        )

        assert custom_result.salt_length == 32
        assert custom_result.iterations == 31
        assert len(custom_result.salt) == 32

    def test_all_algorithms_work(self, make_service):
        service = make_service()
        data = b"test_all_algos"

        for version in AlgorithmVersion:
            result = service.hash(data, algorithm_version=version)
            assert result.algorithm_version == version

            verification = service.verify(data, result)
            assert verification.success is True


class TestExceptionHierarchy:
    def test_all_exceptions_inherit_from_crypto_hash_error(self):
        assert issubclass(AlgorithmNotFoundError, CryptoHashError)
        assert issubclass(InvalidHashFormatError, CryptoHashError)
        assert issubclass(InvalidSaltError, CryptoHashError)
        assert issubclass(HashVerificationError, CryptoHashError)
        assert issubclass(SaltTamperedError, CryptoHashError)
