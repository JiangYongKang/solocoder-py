from __future__ import annotations


class APIKeyError(Exception):
    pass


class APIKeyNotFoundError(APIKeyError):
    pass


class APIKeyRevokedError(APIKeyError):
    pass


class APIKeyPermissionDeniedError(APIKeyError):
    pass


class InvalidAPIKeyError(APIKeyError):
    pass


class APIKeyPrefixCollisionError(APIKeyError):
    pass
