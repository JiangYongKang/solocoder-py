from __future__ import annotations


class OAuth2Error(Exception):
    pass


class PKCEError(OAuth2Error):
    pass


class UnsupportedChallengeMethodError(PKCEError):
    pass


class CodeVerifierMismatchError(PKCEError):
    pass


class StateError(OAuth2Error):
    pass


class StateMissingError(StateError):
    pass


class StateInvalidError(StateError):
    pass


class StateAlreadyUsedError(StateError):
    pass


class AuthorizationCodeError(OAuth2Error):
    pass


class AuthorizationCodeNotFoundError(AuthorizationCodeError):
    pass


class AuthorizationCodeExpiredError(AuthorizationCodeError):
    pass


class AuthorizationCodeAlreadyConsumedError(AuthorizationCodeError):
    pass


class AuthorizationSessionNotFoundError(OAuth2Error):
    pass


class InvalidParameterError(OAuth2Error):
    pass
