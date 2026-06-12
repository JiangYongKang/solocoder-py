from __future__ import annotations


class CredentialRotatorError(Exception):
    pass


class RotationNotFoundError(CredentialRotatorError):
    pass


class RotationAlreadyExistsError(CredentialRotatorError):
    pass


class InvalidRotationPhaseError(CredentialRotatorError):
    pass


class InvalidTrafficPercentageError(CredentialRotatorError):
    pass


class InvalidConfigError(CredentialRotatorError):
    pass


class WriteFailureError(CredentialRotatorError):
    pass
