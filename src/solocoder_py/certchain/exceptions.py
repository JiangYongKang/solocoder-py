from __future__ import annotations


class CertChainError(Exception):
    pass


class CertificateNotFoundError(CertChainError):
    def __init__(self, issuer: str) -> None:
        super().__init__(f"Issuer certificate not found for: {issuer}")
        self.issuer = issuer


class CertificateExpiredError(CertChainError):
    def __init__(self, subject: str, not_after: float, now: float) -> None:
        super().__init__(
            f"Certificate '{subject}' expired at {not_after}, current time is {now}"
        )
        self.subject = subject
        self.not_after = not_after
        self.now = now


class CertificateNotYetValidError(CertChainError):
    def __init__(self, subject: str, not_before: float, now: float) -> None:
        super().__init__(
            f"Certificate '{subject}' not valid before {not_before}, current time is {now}"
        )
        self.subject = subject
        self.not_before = not_before
        self.now = now


class CertificateRevokedError(CertChainError):
    def __init__(self, subject: str, serial_number: int, issuer: str) -> None:
        super().__init__(
            f"Certificate '{subject}' (serial={serial_number}) has been revoked by issuer '{issuer}'"
        )
        self.subject = subject
        self.serial_number = serial_number
        self.issuer = issuer


class InvalidSignatureError(CertChainError):
    def __init__(self, subject: str, claimed_issuer: str) -> None:
        super().__init__(
            f"Certificate '{subject}' signature does not match claimed issuer '{claimed_issuer}'"
        )
        self.subject = subject
        self.claimed_issuer = claimed_issuer


class ChainBrokenError(CertChainError):
    def __init__(self, subject: str, issuer: str) -> None:
        super().__init__(
            f"Chain broken: cannot find issuer '{issuer}' for certificate '{subject}'"
        )
        self.subject = subject
        self.issuer = issuer


class TrustAnchorNotFoundError(CertChainError):
    def __init__(self, top_subject: str, top_issuer: str) -> None:
        super().__init__(
            f"Certificate chain top '{top_subject}' issuer '{top_issuer}' not found in trust anchors"
        )
        self.top_subject = top_subject
        self.top_issuer = top_issuer


class EmptyTrustAnchorError(CertChainError):
    def __init__(self) -> None:
        super().__init__("Trust anchor list is empty")


class CRLExpiredError(CertChainError):
    def __init__(self, issuer: str, next_update: float, now: float) -> None:
        super().__init__(
            f"CRL for issuer '{issuer}' expired at {next_update}, current time is {now}"
        )
        self.issuer = issuer
        self.next_update = next_update
        self.now = now


class CRLFetchError(CertChainError):
    def __init__(self, issuer: str, reason: str) -> None:
        super().__init__(f"Failed to fetch CRL for issuer '{issuer}': {reason}")
        self.issuer = issuer
        self.reason = reason


class CRLNotFoundError(CertChainError):
    def __init__(self, issuer: str) -> None:
        super().__init__(f"CRL not found for issuer: {issuer}")
        self.issuer = issuer


__all__ = [
    "CertChainError",
    "CertificateNotFoundError",
    "CertificateExpiredError",
    "CertificateNotYetValidError",
    "CertificateRevokedError",
    "InvalidSignatureError",
    "ChainBrokenError",
    "TrustAnchorNotFoundError",
    "EmptyTrustAnchorError",
    "CRLExpiredError",
    "CRLFetchError",
    "CRLNotFoundError",
]
