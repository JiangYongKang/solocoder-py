from __future__ import annotations


class QuotaError(Exception):
    pass


class TenantError(QuotaError):
    pass


class TenantNotFoundError(TenantError):
    pass


class TenantExistsError(TenantError):
    pass


class QuotaLimitExceededError(TenantError):
    def __init__(self, message: str, reason: str) -> None:
        super().__init__(message)
        self.reason = reason


class InvalidQuotaAmountError(TenantError):
    pass


class ReleaseExceedUsedError(TenantError):
    pass


class GlobalQuotaNotSetError(QuotaError):
    pass
