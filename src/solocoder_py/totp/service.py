from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from typing import Optional

from .exceptions import (
    InvalidDriftWindowError,
    InvalidSecretError,
    RecoveryCodeConsumedError,
    SecretAlreadyExistsError,
    SecretNotFoundError,
)
from .models import (
    GenerateSecretResult,
    RecoveryCode,
    TotpSecret,
    UserTotpRecord,
    VerificationResult,
)
from .store import InMemoryTotpStore


DEFAULT_SECRET_BYTES = 20
DEFAULT_DIGITS = 6
DEFAULT_PERIOD = 30
DEFAULT_ALGORITHM = "SHA1"
DEFAULT_DRIFT_WINDOWS = 1
DEFAULT_RECOVERY_CODE_COUNT = 8
DEFAULT_RECOVERY_CODE_BYTES = 16


def _base32_encode(data: bytes) -> str:
    return base64.b32encode(data).decode("ascii").rstrip("=")


def _base32_decode(encoded: str) -> bytes:
    padding = 8 - len(encoded) % 8
    if padding != 8:
        encoded += "=" * padding
    try:
        return base64.b32decode(encoded.upper())
    except (ValueError, base64.binascii.Error) as e:
        raise InvalidSecretError(f"Invalid Base32 secret: {e}") from e


def generate_secret(secret_bytes: int = DEFAULT_SECRET_BYTES) -> str:
    if secret_bytes < 16:
        raise InvalidSecretError("Secret must be at least 16 bytes (128 bits)")
    random_bytes = secrets.token_bytes(secret_bytes)
    return _base32_encode(random_bytes)


def generate_recovery_codes(count: int = DEFAULT_RECOVERY_CODE_COUNT) -> list[str]:
    if count < 1:
        raise ValueError("Recovery code count must be at least 1")
    codes = []
    for _ in range(count):
        raw = secrets.token_bytes(DEFAULT_RECOVERY_CODE_BYTES)
        code = _base32_encode(raw).lower()
        codes.append(code)
    return codes


def _hash_recovery_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _hotp(key: bytes, counter: int, digits: int = 6) -> str:
    counter_bytes = struct.pack(">Q", counter)
    hs = hmac.new(key, counter_bytes, hashlib.sha1).digest()
    offset = hs[-1] & 0x0F
    binary = struct.unpack(">I", hs[offset : offset + 4])[0] & 0x7FFFFFFF
    otp = binary % (10**digits)
    return str(otp).zfill(digits)


def _get_counter(period: int, timestamp: Optional[int] = None) -> int:
    if timestamp is None:
        timestamp = int(time.time())
    return timestamp // period


def compute_totp(
    secret: str,
    digits: int = DEFAULT_DIGITS,
    period: int = DEFAULT_PERIOD,
    timestamp: Optional[int] = None,
) -> str:
    key = _base32_decode(secret)
    counter = _get_counter(period, timestamp)
    return _hotp(key, counter, digits)


class TotpService:
    def __init__(
        self,
        issuer: str = "SoloCoder",
        secret_bytes: int = DEFAULT_SECRET_BYTES,
        digits: int = DEFAULT_DIGITS,
        period: int = DEFAULT_PERIOD,
        drift_windows: int = DEFAULT_DRIFT_WINDOWS,
        recovery_code_count: int = DEFAULT_RECOVERY_CODE_COUNT,
        store: Optional[InMemoryTotpStore] = None,
    ) -> None:
        if drift_windows < 0:
            raise InvalidDriftWindowError("Drift windows must be non-negative")
        if secret_bytes < 16:
            raise InvalidSecretError("Secret must be at least 16 bytes (128 bits)")
        if digits < 6 or digits > 8:
            raise ValueError("Digits must be between 6 and 8")
        if period < 1:
            raise ValueError("Period must be at least 1 second")
        if recovery_code_count < 1:
            raise ValueError("Recovery code count must be at least 1")

        self.issuer = issuer
        self.secret_bytes = secret_bytes
        self.digits = digits
        self.period = period
        self.drift_windows = drift_windows
        self.recovery_code_count = recovery_code_count
        self.store = store if store is not None else InMemoryTotpStore()

    def generate_secret_for_user(
        self,
        user_id: str,
        overwrite: bool = False,
    ) -> GenerateSecretResult:
        if not overwrite and self.store.has_record(user_id):
            raise SecretAlreadyExistsError(f"TOTP secret already exists for user {user_id}")

        secret_str = generate_secret(self.secret_bytes)
        totp_secret = TotpSecret(
            user_id=user_id,
            secret=secret_str,
            issuer=self.issuer,
            digits=self.digits,
            period=self.period,
            algorithm=DEFAULT_ALGORITHM,
        )

        recovery_codes_plain = generate_recovery_codes(self.recovery_code_count)
        recovery_codes = [
            RecoveryCode(code_hash=_hash_recovery_code(code))
            for code in recovery_codes_plain
        ]

        record = UserTotpRecord(
            user_id=user_id,
            secret=totp_secret,
            recovery_codes=recovery_codes,
        )
        self.store.store_record(user_id, record)

        return GenerateSecretResult(
            user_id=user_id,
            secret=secret_str,
            uri=totp_secret.get_uri(),
            recovery_codes=recovery_codes_plain,
        )

    def generate_secrets_for_users(
        self,
        user_ids: list[str],
        overwrite: bool = False,
    ) -> list[GenerateSecretResult]:
        results = []
        for user_id in user_ids:
            result = self.generate_secret_for_user(user_id, overwrite=overwrite)
            results.append(result)
        return results

    def verify_totp(
        self,
        user_id: str,
        code: str,
        drift_windows: Optional[int] = None,
    ) -> VerificationResult:
        record = self.store.get_record(user_id)
        if record is None:
            raise SecretNotFoundError(f"No TOTP secret found for user {user_id}")

        if drift_windows is None:
            drift_windows = self.drift_windows
        if drift_windows < 0:
            raise InvalidDriftWindowError("Drift windows must be non-negative")

        secret = record.secret
        key = _base32_decode(secret.secret)
        current_counter = _get_counter(secret.period)

        record.cleanup_old_windows(current_counter, drift_windows)

        for offset in range(-drift_windows, drift_windows + 1):
            counter = current_counter + offset
            if counter < 0:
                continue
            expected_code = _hotp(key, counter, secret.digits)
            if secrets.compare_digest(expected_code, code):
                if record.is_code_used(counter, code):
                    return VerificationResult(success=False)
                record.mark_code_used(counter, code)
                return VerificationResult(
                    success=True,
                    method="totp",
                    recovery_codes_remaining=self._count_remaining_recovery_codes(record),
                )

        return VerificationResult(success=False)

    def verify_recovery_code(
        self,
        user_id: str,
        code: str,
    ) -> VerificationResult:
        record = self.store.get_record(user_id)
        if record is None:
            raise SecretNotFoundError(f"No TOTP secret found for user {user_id}")

        normalized_code = code.strip().lower()
        code_hash = _hash_recovery_code(normalized_code)

        for recovery_code in record.recovery_codes:
            if secrets.compare_digest(recovery_code.code_hash, code_hash):
                if recovery_code.consumed:
                    raise RecoveryCodeConsumedError("Recovery code has already been used")
                recovery_code.consumed = True
                return VerificationResult(
                    success=True,
                    method="recovery_code",
                    recovery_codes_remaining=self._count_remaining_recovery_codes(record),
                )

        return VerificationResult(success=False)

    def regenerate_recovery_codes(self, user_id: str) -> list[str]:
        record = self.store.get_record(user_id)
        if record is None:
            raise SecretNotFoundError(f"No TOTP secret found for user {user_id}")

        new_codes_plain = generate_recovery_codes(self.recovery_code_count)
        new_codes = [
            RecoveryCode(code_hash=_hash_recovery_code(code))
            for code in new_codes_plain
        ]
        record.recovery_codes = new_codes
        return new_codes_plain

    def get_recovery_codes_remaining(self, user_id: str) -> int:
        record = self.store.get_record(user_id)
        if record is None:
            raise SecretNotFoundError(f"No TOTP secret found for user {user_id}")
        return self._count_remaining_recovery_codes(record)

    def has_secret(self, user_id: str) -> bool:
        return self.store.has_record(user_id)

    def get_secret_uri(self, user_id: str) -> str:
        record = self.store.get_record(user_id)
        if record is None:
            raise SecretNotFoundError(f"No TOTP secret found for user {user_id}")
        return record.secret.get_uri()

    def delete_secret(self, user_id: str) -> bool:
        return self.store.delete_record(user_id)

    def _count_remaining_recovery_codes(self, record: UserTotpRecord) -> int:
        return sum(1 for rc in record.recovery_codes if not rc.consumed)
