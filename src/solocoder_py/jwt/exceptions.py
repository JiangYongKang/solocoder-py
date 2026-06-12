from __future__ import annotations


class JWTError(Exception):
    pass


class MalformedTokenError(JWTError):
    pass


class InvalidSignatureError(JWTError):
    pass


class InvalidAlgorithmError(JWTError):
    pass


class KeyNotFoundError(JWTError):
    def __init__(self, kid: str) -> None:
        super().__init__(f"Signing key with kid '{kid}' not found")
        self.kid = kid


class EmptyKeyStoreError(JWTError):
    pass


class ExpiredTokenError(JWTError):
    def __init__(self, exp: float, now: float) -> None:
        super().__init__(f"Token expired at {exp}, current time is {now}")
        self.exp = exp
        self.now = now


class ImmatureTokenError(JWTError):
    def __init__(self, nbf: float, now: float) -> None:
        super().__init__(f"Token not valid before {nbf}, current time is {now}")
        self.nbf = nbf
        self.now = now


class InvalidIssuerError(JWTError):
    def __init__(self, iss: str, allowed: list[str]) -> None:
        super().__init__(f"Invalid issuer '{iss}', allowed: {allowed}")
        self.iss = iss
        self.allowed = allowed


class InvalidAudienceError(JWTError):
    def __init__(self, aud, expected: str) -> None:
        super().__init__(f"Invalid audience '{aud}', expected to contain '{expected}'")
        self.aud = aud
        self.expected = expected


class MissingClaimError(JWTError):
    def __init__(self, claim: str) -> None:
        super().__init__(f"Missing required claim: '{claim}'")
        self.claim = claim
