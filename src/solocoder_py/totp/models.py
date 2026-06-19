from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TotpSecret:
    user_id: str
    secret: str
    issuer: str
    digits: int = 6
    period: int = 30
    algorithm: str = "SHA1"

    def get_uri(self) -> str:
        from urllib.parse import quote

        issuer_encoded = quote(self.issuer, safe="")
        user_encoded = quote(self.user_id, safe="")
        label = f"{issuer_encoded}:{user_encoded}"
        params = (
            f"secret={self.secret}"
            f"&issuer={issuer_encoded}"
            f"&algorithm={self.algorithm}"
            f"&digits={self.digits}"
            f"&period={self.period}"
        )
        return f"otpauth://totp/{label}?{params}"


@dataclass
class RecoveryCode:
    code_hash: str
    consumed: bool = False


@dataclass
class UserTotpRecord:
    user_id: str
    secret: TotpSecret
    recovery_codes: list[RecoveryCode] = field(default_factory=list)
    used_codes: dict[int, set[str]] = field(default_factory=dict)

    def cleanup_old_windows(self, current_counter: int, drift_windows: int) -> None:
        oldest_valid = current_counter - drift_windows
        expired = [counter for counter in self.used_codes if counter < oldest_valid]
        for counter in expired:
            del self.used_codes[counter]

    def is_code_used(self, counter: int, code: str) -> bool:
        codes = self.used_codes.get(counter)
        if codes is None:
            return False
        return code in codes

    def mark_code_used(self, counter: int, code: str) -> None:
        if counter not in self.used_codes:
            self.used_codes[counter] = set()
        self.used_codes[counter].add(code)


@dataclass
class GenerateSecretResult:
    user_id: str
    secret: str
    uri: str
    recovery_codes: list[str]


@dataclass
class VerificationResult:
    success: bool
    method: Optional[str] = None
    recovery_codes_remaining: Optional[int] = None
