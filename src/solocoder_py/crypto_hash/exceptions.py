from __future__ import annotations


class CryptoHashError(Exception):
    pass


class AlgorithmNotFoundError(CryptoHashError):
    pass


class InvalidHashFormatError(CryptoHashError):
    pass


class InvalidSaltError(CryptoHashError):
    pass


class HashVerificationError(CryptoHashError):
    pass


class SaltTamperedError(CryptoHashError):
    pass
