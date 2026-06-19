from __future__ import annotations

import base64
import time

import pytest

from solocoder_py.totp import (
    DEFAULT_DRIFT_WINDOWS,
    DEFAULT_RECOVERY_CODE_COUNT,
    DEFAULT_SECRET_BYTES,
    InMemoryTotpStore,
    InvalidDriftWindowError,
    InvalidRecoveryCodeError,
    InvalidSecretError,
    InvalidTotpCodeError,
    RecoveryCodeConsumedError,
    SecretAlreadyExistsError,
    SecretNotFoundError,
    SUPPORTED_ALGORITHMS,
    TotpService,
    compute_totp,
    generate_recovery_codes,
    generate_secret,
)


# ============================================================
# Normal Flows
# ============================================================

class TestSecretGeneration:
    def test_generate_secret_is_base32_valid(self):
        secret = generate_secret()
        assert isinstance(secret, str)
        assert len(secret) > 0
        padded = secret + "=" * ((8 - len(secret) % 8) % 8)
        decoded = base64.b32decode(padded.upper())
        assert len(decoded) == DEFAULT_SECRET_BYTES

    def test_generate_secret_minimum_entropy(self):
        secret = generate_secret(20)
        padded = secret + "=" * ((8 - len(secret) % 8) % 8)
        decoded = base64.b32decode(padded.upper())
        assert len(decoded) >= 20

    def test_generate_secret_randomness(self):
        secrets = [generate_secret() for _ in range(100)]
        assert len(set(secrets)) == 100

    def test_generate_secret_custom_length(self):
        secret = generate_secret(32)
        padded = secret + "=" * ((8 - len(secret) % 8) % 8)
        decoded = base64.b32decode(padded.upper())
        assert len(decoded) == 32

    def test_generate_secret_for_user_returns_uri(self, make_service):
        service = make_service()
        result = service.generate_secret_for_user("user1")

        assert result.user_id == "user1"
        assert result.secret is not None
        assert result.uri.startswith("otpauth://totp/")
        assert "secret=" in result.uri
        assert "issuer=" in result.uri
        assert "digits=" in result.uri
        assert "period=" in result.uri
        assert "algorithm=" in result.uri
        assert "user1" in result.uri

    def test_generate_secret_for_user_returns_recovery_codes(self, make_service):
        service = make_service()
        result = service.generate_secret_for_user("user1")

        assert len(result.recovery_codes) == DEFAULT_RECOVERY_CODE_COUNT
        for code in result.recovery_codes:
            assert isinstance(code, str)
            assert len(code) > 0

    def test_generate_secrets_for_multiple_users(self, make_service):
        service = make_service()
        user_ids = ["alice", "bob", "charlie"]
        results = service.generate_secrets_for_users(user_ids)

        assert len(results) == 3
        secrets = [r.secret for r in results]
        assert len(set(secrets)) == 3
        for result in results:
            assert result.user_id in user_ids
            assert result.uri.startswith("otpauth://totp/")

    def test_get_secret_uri_after_generation(self, make_service):
        service = make_service(issuer="MyApp")
        service.generate_secret_for_user("user1")
        uri = service.get_secret_uri("user1")
        assert uri.startswith("otpauth://totp/")
        assert "MyApp" in uri

    def test_has_secret_true_after_generation(self, make_service):
        service = make_service()
        assert service.has_secret("user1") is False
        service.generate_secret_for_user("user1")
        assert service.has_secret("user1") is True


class TestTotpVerification:
    def test_correct_totp_code_verifies(self, make_service):
        service = make_service()
        result = service.generate_secret_for_user("user1")
        secret = result.secret

        code = compute_totp(secret)
        verification = service.verify_totp("user1", code)

        assert verification.success is True
        assert verification.method == "totp"

    def test_compute_totp_returns_digits_length(self):
        secret = generate_secret()
        code = compute_totp(secret, digits=6)
        assert len(code) == 6
        assert code.isdigit()

    def test_compute_totp_custom_digits(self):
        secret = generate_secret()
        code = compute_totp(secret, digits=8)
        assert len(code) == 8
        assert code.isdigit()

    def test_compute_totp_deterministic_at_same_time(self):
        secret = generate_secret()
        now = int(time.time())
        code1 = compute_totp(secret, timestamp=now)
        code2 = compute_totp(secret, timestamp=now)
        assert code1 == code2

    def test_compute_totp_changes_over_time(self):
        secret = generate_secret()
        now = int(time.time())
        code_now = compute_totp(secret, timestamp=now)
        code_future = compute_totp(secret, timestamp=now + 60)
        assert code_now != code_future


class TestAlgorithmSupport:
    def test_different_algorithms_produce_different_codes(self):
        secret = generate_secret()
        now = int(time.time())

        code_sha1 = compute_totp(secret, algorithm="SHA1", timestamp=now)
        code_sha256 = compute_totp(secret, algorithm="SHA256", timestamp=now)
        code_sha512 = compute_totp(secret, algorithm="SHA512", timestamp=now)

        assert code_sha1 != code_sha256
        assert code_sha1 != code_sha512
        assert code_sha256 != code_sha512

    def test_service_uses_configured_algorithm(self):
        service_sha1 = TotpService(algorithm="SHA1")
        service_sha256 = TotpService(algorithm="SHA256")

        result1 = service_sha1.generate_secret_for_user("user1")
        result256 = service_sha256.generate_secret_for_user("user2")

        assert service_sha1.algorithm == "SHA1"
        assert service_sha256.algorithm == "SHA256"

        now = int(time.time())
        code_sha1 = compute_totp(result1.secret, algorithm="SHA1", timestamp=now)
        code_sha256 = compute_totp(result256.secret, algorithm="SHA256", timestamp=now)

        verification1 = service_sha1.verify_totp("user1", code_sha1)
        verification256 = service_sha256.verify_totp("user2", code_sha256)

        assert verification1.success is True
        assert verification256.success is True

    def test_service_algorithm_mismatch_fails(self):
        service_sha1 = TotpService(algorithm="SHA1")
        result = service_sha1.generate_secret_for_user("user1")

        now = int(time.time())
        code_sha256 = compute_totp(result.secret, algorithm="SHA256", timestamp=now)

        with pytest.raises(InvalidTotpCodeError):
            service_sha1.verify_totp("user1", code_sha256)

    def test_unsupported_algorithm_raises(self):
        with pytest.raises(InvalidSecretError, match="Unsupported algorithm"):
            compute_totp(generate_secret(), algorithm="MD5")

    def test_service_unsupported_algorithm_raises(self):
        with pytest.raises(InvalidSecretError, match="Unsupported algorithm"):
            TotpService(algorithm="MD5")

    def test_supported_algorithms_constant(self):
        assert SUPPORTED_ALGORITHMS == {"SHA1", "SHA256", "SHA512"}

    def test_uri_includes_algorithm(self):
        service = TotpService(algorithm="SHA256", issuer="TestApp")
        result = service.generate_secret_for_user("user1")
        assert "algorithm=SHA256" in result.uri

    def test_secret_model_stores_algorithm(self):
        from solocoder_py.totp import TotpSecret

        ts = TotpSecret(user_id="u", secret="TEST", issuer="Test", algorithm="SHA512")
        assert ts.algorithm == "SHA512"
        assert "algorithm=SHA512" in ts.get_uri()


class TestDriftTolerance:
    def test_drift_tolerance_previous_window(self, make_service):
        service = make_service(drift_windows=1)
        result = service.generate_secret_for_user("user1")
        secret = result.secret

        now = int(time.time())
        past_code = compute_totp(secret, timestamp=now - 30)

        verification = service.verify_totp("user1", past_code)
        assert verification.success is True

    def test_drift_tolerance_next_window(self, make_service):
        service = make_service(drift_windows=1)
        result = service.generate_secret_for_user("user1")
        secret = result.secret

        now = int(time.time())
        future_code = compute_totp(secret, timestamp=now + 30)

        verification = service.verify_totp("user1", future_code)
        assert verification.success is True

    def test_drift_tolerance_current_window(self, make_service):
        service = make_service(drift_windows=1)
        result = service.generate_secret_for_user("user1")
        secret = result.secret

        now = int(time.time())
        current_code = compute_totp(secret, timestamp=now)

        verification = service.verify_totp("user1", current_code)
        assert verification.success is True

    def test_drift_tolerance_two_windows(self, make_service):
        service = make_service(drift_windows=2)
        result = service.generate_secret_for_user("user1")
        secret = result.secret

        now = int(time.time())
        code_two_back = compute_totp(secret, timestamp=now - 60)

        verification = service.verify_totp("user1", code_two_back)
        assert verification.success is True


class TestReplayProtection:
    def test_same_code_cannot_be_used_twice_same_window(self, make_service):
        service = make_service(drift_windows=1)
        result = service.generate_secret_for_user("user1")
        secret = result.secret

        code = compute_totp(secret)

        first = service.verify_totp("user1", code)
        assert first.success is True

        with pytest.raises(InvalidTotpCodeError):
            service.verify_totp("user1", code)

    def test_replay_with_drift_windows(self, make_service):
        service = make_service(drift_windows=2)
        result = service.generate_secret_for_user("user1")
        secret = result.secret

        now = int(time.time())
        code = compute_totp(secret, timestamp=now - 30)

        first = service.verify_totp("user1", code)
        assert first.success is True

        with pytest.raises(InvalidTotpCodeError):
            service.verify_totp("user1", code)


class TestRecoveryCodes:
    def test_recovery_code_verification_success(self, make_service):
        service = make_service()
        result = service.generate_secret_for_user("user1")
        recovery_code = result.recovery_codes[0]

        verification = service.verify_recovery_code("user1", recovery_code)
        assert verification.success is True
        assert verification.method == "recovery_code"
        assert verification.recovery_codes_remaining == DEFAULT_RECOVERY_CODE_COUNT - 1

    def test_recovery_code_can_only_be_used_once(self, make_service):
        service = make_service()
        result = service.generate_secret_for_user("user1")
        recovery_code = result.recovery_codes[0]

        first = service.verify_recovery_code("user1", recovery_code)
        assert first.success is True

        with pytest.raises(RecoveryCodeConsumedError):
            service.verify_recovery_code("user1", recovery_code)

    def test_recovery_code_case_insensitive(self, make_service):
        service = make_service()
        result = service.generate_secret_for_user("user1")
        recovery_code = result.recovery_codes[0]

        verification = service.verify_recovery_code("user1", recovery_code.upper())
        assert verification.success is True

    def test_recovery_code_with_whitespace(self, make_service):
        service = make_service()
        result = service.generate_secret_for_user("user1")
        recovery_code = result.recovery_codes[0]

        verification = service.verify_recovery_code("user1", f"  {recovery_code}  ")
        assert verification.success is True

    def test_get_recovery_codes_remaining(self, make_service):
        service = make_service()
        result = service.generate_secret_for_user("user1")
        codes = result.recovery_codes

        remaining = service.get_recovery_codes_remaining("user1")
        assert remaining == DEFAULT_RECOVERY_CODE_COUNT

        service.verify_recovery_code("user1", codes[0])
        remaining = service.get_recovery_codes_remaining("user1")
        assert remaining == DEFAULT_RECOVERY_CODE_COUNT - 1

    def test_regenerate_recovery_codes(self, make_service):
        service = make_service()
        result = service.generate_secret_for_user("user1")
        old_codes = result.recovery_codes

        new_codes = service.regenerate_recovery_codes("user1")
        assert len(new_codes) == DEFAULT_RECOVERY_CODE_COUNT
        assert set(new_codes) != set(old_codes)

        for old_code in old_codes:
            with pytest.raises(InvalidRecoveryCodeError):
                service.verify_recovery_code("user1", old_code)

    def test_regenerate_recovery_codes_after_all_consumed(self, make_service):
        service = make_service()
        result = service.generate_secret_for_user("user1")
        codes = result.recovery_codes

        for code in codes:
            service.verify_recovery_code("user1", code)

        remaining = service.get_recovery_codes_remaining("user1")
        assert remaining == 0

        new_codes = service.regenerate_recovery_codes("user1")
        assert len(new_codes) == DEFAULT_RECOVERY_CODE_COUNT

        remaining = service.get_recovery_codes_remaining("user1")
        assert remaining == DEFAULT_RECOVERY_CODE_COUNT

        verification = service.verify_recovery_code("user1", new_codes[0])
        assert verification.success is True

    def test_generate_recovery_codes_function(self):
        codes = generate_recovery_codes(10)
        assert len(codes) == 10
        assert len(set(codes)) == 10
        for code in codes:
            assert isinstance(code, str)
            assert len(code) > 0


# ============================================================
# Boundary Conditions
# ============================================================

class TestBoundaryConditions:
    def test_zero_drift_windows_only_checks_current(self, make_service):
        service = make_service(drift_windows=0)
        result = service.generate_secret_for_user("user1")
        secret = result.secret

        now = int(time.time())
        current_code = compute_totp(secret, timestamp=now)
        past_code = compute_totp(secret, timestamp=now - 30)
        future_code = compute_totp(secret, timestamp=now + 30)

        assert service.verify_totp("user1", current_code).success is True
        with pytest.raises(InvalidTotpCodeError):
            service.verify_totp("user1", past_code)
        with pytest.raises(InvalidTotpCodeError):
            service.verify_totp("user1", future_code)

    def test_minimum_secret_bytes(self):
        with pytest.raises(InvalidSecretError):
            generate_secret(16)

    def test_secret_bytes_at_boundary_20(self):
        secret = generate_secret(20)
        padded = secret + "=" * ((8 - len(secret) % 8) % 8)
        decoded = base64.b32decode(padded.upper())
        assert len(decoded) == 20

    def test_service_minimum_secret_bytes(self):
        with pytest.raises(InvalidSecretError):
            TotpService(secret_bytes=16)

    def test_all_recovery_codes_consumed_then_regenerate(self, make_service):
        service = make_service()
        result = service.generate_secret_for_user("user1")
        codes = result.recovery_codes

        for i, code in enumerate(codes):
            verification = service.verify_recovery_code("user1", code)
            assert verification.success is True
            assert verification.recovery_codes_remaining == DEFAULT_RECOVERY_CODE_COUNT - i - 1

        remaining = service.get_recovery_codes_remaining("user1")
        assert remaining == 0

        new_codes = service.regenerate_recovery_codes("user1")
        assert len(new_codes) == DEFAULT_RECOVERY_CODE_COUNT

        remaining = service.get_recovery_codes_remaining("user1")
        assert remaining == DEFAULT_RECOVERY_CODE_COUNT

        verification = service.verify_recovery_code("user1", new_codes[-1])
        assert verification.success is True

    def test_overwrite_existing_secret(self, make_service):
        service = make_service()
        result1 = service.generate_secret_for_user("user1")
        result2 = service.generate_secret_for_user("user1", overwrite=True)

        assert result1.secret != result2.secret

    def test_delete_secret(self, make_service):
        service = make_service()
        service.generate_secret_for_user("user1")
        assert service.has_secret("user1") is True

        result = service.delete_secret("user1")
        assert result is True
        assert service.has_secret("user1") is False

    def test_delete_nonexistent_secret(self, make_service):
        service = make_service()
        result = service.delete_secret("nonexistent")
        assert result is False

    def test_secret_length_boundary_large(self):
        secret = generate_secret(64)
        padded = secret + "=" * ((8 - len(secret) % 8) % 8)
        decoded = base64.b32decode(padded.upper())
        assert len(decoded) == 64

    def test_compute_totp_digits_boundary_6(self):
        secret = generate_secret()
        code = compute_totp(secret, digits=6)
        assert len(code) == 6

    def test_compute_totp_digits_boundary_8(self):
        secret = generate_secret()
        code = compute_totp(secret, digits=8)
        assert len(code) == 8

    def test_single_recovery_code(self):
        codes = generate_recovery_codes(1)
        assert len(codes) == 1


# ============================================================
# Exception / Error Branches
# ============================================================

class TestExceptionCases:
    def test_wrong_totp_code_rejected(self, make_service):
        service = make_service()
        service.generate_secret_for_user("user1")

        with pytest.raises(InvalidTotpCodeError):
            service.verify_totp("user1", "000000")

    def test_used_totp_code_replay_rejected(self, make_service):
        service = make_service(drift_windows=1)
        result = service.generate_secret_for_user("user1")
        secret = result.secret

        code = compute_totp(secret)

        first = service.verify_totp("user1", code)
        assert first.success is True

        with pytest.raises(InvalidTotpCodeError):
            service.verify_totp("user1", code)

    def test_code_outside_drift_window_rejected(self, make_service):
        service = make_service(drift_windows=1)
        result = service.generate_secret_for_user("user1")
        secret = result.secret

        now = int(time.time())
        code_far_future = compute_totp(secret, timestamp=now + 120)

        with pytest.raises(InvalidTotpCodeError):
            service.verify_totp("user1", code_far_future)

    def test_consumed_recovery_code_rejected(self, make_service):
        service = make_service()
        result = service.generate_secret_for_user("user1")
        code = result.recovery_codes[0]

        service.verify_recovery_code("user1", code)

        with pytest.raises(RecoveryCodeConsumedError):
            service.verify_recovery_code("user1", code)

    def test_nonexistent_user_secret_query(self, make_service):
        service = make_service()

        with pytest.raises(SecretNotFoundError):
            service.get_secret_uri("nonexistent")

    def test_verify_totp_without_secret_raises(self, make_service):
        service = make_service()

        with pytest.raises(SecretNotFoundError):
            service.verify_totp("nonexistent", "123456")

    def test_verify_recovery_code_without_secret_raises(self, make_service):
        service = make_service()

        with pytest.raises(SecretNotFoundError):
            service.verify_recovery_code("nonexistent", "somecode")

    def test_generate_secret_duplicate_without_overwrite(self, make_service):
        service = make_service()
        service.generate_secret_for_user("user1")

        with pytest.raises(SecretAlreadyExistsError):
            service.generate_secret_for_user("user1")

    def test_invalid_base32_secret(self):
        with pytest.raises(InvalidSecretError):
            compute_totp("!@#$%^&*()")

    def test_negative_drift_windows_in_service(self):
        with pytest.raises(InvalidDriftWindowError):
            TotpService(drift_windows=-1)

    def test_negative_drift_windows_in_verify(self, make_service):
        service = make_service()
        service.generate_secret_for_user("user1")

        with pytest.raises(InvalidDriftWindowError):
            service.verify_totp("user1", "123456", drift_windows=-1)

    def test_get_recovery_codes_remaining_no_secret(self, make_service):
        service = make_service()

        with pytest.raises(SecretNotFoundError):
            service.get_recovery_codes_remaining("nonexistent")

    def test_regenerate_recovery_codes_no_secret(self, make_service):
        service = make_service()

        with pytest.raises(SecretNotFoundError):
            service.regenerate_recovery_codes("nonexistent")

    def test_invalid_recovery_code_raises(self, make_service):
        service = make_service()
        service.generate_secret_for_user("user1")

        with pytest.raises(InvalidRecoveryCodeError):
            service.verify_recovery_code("user1", "wrongcode123")

    def test_service_digits_too_low(self):
        with pytest.raises(ValueError):
            TotpService(digits=5)

    def test_service_digits_too_high(self):
        with pytest.raises(ValueError):
            TotpService(digits=9)

    def test_service_period_zero(self):
        with pytest.raises(ValueError):
            TotpService(period=0)

    def test_service_recovery_code_count_zero(self):
        with pytest.raises(ValueError):
            TotpService(recovery_code_count=0)

    def test_generate_recovery_codes_zero_count(self):
        with pytest.raises(ValueError):
            generate_recovery_codes(0)

    def test_invalid_totp_code_error_message(self, make_service):
        service = make_service()
        service.generate_secret_for_user("user1")

        with pytest.raises(InvalidTotpCodeError, match="Invalid TOTP code or code outside drift tolerance window"):
            service.verify_totp("user1", "000000")

    def test_used_totp_code_error_message(self, make_service):
        service = make_service()
        result = service.generate_secret_for_user("user1")
        code = compute_totp(result.secret)

        service.verify_totp("user1", code)

        with pytest.raises(InvalidTotpCodeError, match="TOTP code has already been used in this time window"):
            service.verify_totp("user1", code)


# ============================================================
# Store Tests
# ============================================================

class TestInMemoryTotpStore:
    def test_store_and_retrieve_record(self, make_store, make_service):
        store = make_store()
        service = TotpService(store=store)
        service.generate_secret_for_user("user1")

        record = store.get_record("user1")
        assert record is not None
        assert record.user_id == "user1"

    def test_get_nonexistent_record(self, make_store):
        store = make_store()
        assert store.get_record("nonexistent") is None

    def test_has_record(self, make_store, make_service):
        store = make_store()
        service = TotpService(store=store)

        assert store.has_record("user1") is False
        service.generate_secret_for_user("user1")
        assert store.has_record("user1") is True

    def test_delete_record(self, make_store, make_service):
        store = make_store()
        service = TotpService(store=store)
        service.generate_secret_for_user("user1")

        assert store.delete_record("user1") is True
        assert store.get_record("user1") is None
        assert store.delete_record("user1") is False

    def test_clear_store(self, make_store, make_service):
        store = make_store()
        service = TotpService(store=store)
        service.generate_secret_for_user("user1")
        service.generate_secret_for_user("user2")

        assert len(store) == 2
        store.clear()
        assert len(store) == 0

    def test_store_len(self, make_store, make_service):
        store = make_store()
        service = TotpService(store=store)

        assert len(store) == 0
        service.generate_secret_for_user("user1")
        assert len(store) == 1
        service.generate_secret_for_user("user2")
        assert len(store) == 2


# ============================================================
# Exception Hierarchy
# ============================================================

class TestExceptionHierarchy:
    def test_all_exceptions_inherit_from_totp_error(self):
        from solocoder_py.totp import TotpError
        from solocoder_py.totp import (
            SecretNotFoundError,
            SecretAlreadyExistsError,
            InvalidTotpCodeError,
            InvalidRecoveryCodeError,
            RecoveryCodeConsumedError,
            InvalidSecretError,
            InvalidDriftWindowError,
        )

        assert issubclass(SecretNotFoundError, TotpError)
        assert issubclass(SecretAlreadyExistsError, TotpError)
        assert issubclass(InvalidTotpCodeError, TotpError)
        assert issubclass(InvalidRecoveryCodeError, TotpError)
        assert issubclass(RecoveryCodeConsumedError, TotpError)
        assert issubclass(InvalidSecretError, TotpError)
        assert issubclass(InvalidDriftWindowError, TotpError)

    def test_invalid_totp_code_is_totp_error(self):
        from solocoder_py.totp import TotpError, InvalidTotpCodeError

        assert issubclass(InvalidTotpCodeError, TotpError)

    def test_invalid_recovery_code_is_totp_error(self):
        from solocoder_py.totp import TotpError, InvalidRecoveryCodeError

        assert issubclass(InvalidRecoveryCodeError, TotpError)
