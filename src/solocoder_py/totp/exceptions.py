from __future__ import annotations


class TotpError(Exception):
    pass


class SecretNotFoundError(TotpError):
    pass


class SecretAlreadyExistsError(TotpError):
    pass


class InvalidTotpCodeError(TotpError):
    pass


class InvalidRecoveryCodeError(TotpError):
    pass


class RecoveryCodeConsumedError(TotpError):
    pass


class InvalidSecretError(TotpError):
    pass


class InvalidDriftWindowError(TotpError):
    pass
