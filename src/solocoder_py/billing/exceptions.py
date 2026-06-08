from __future__ import annotations


class BillingError(Exception):
    pass


class PricingNotFoundError(BillingError):
    pass


class InvalidTierConfigError(BillingError):
    pass


class FutureUsageError(BillingError):
    pass


class PeriodSettledError(BillingError):
    pass


class InvalidPeriodError(BillingError):
    pass


class AccountNotFoundError(BillingError):
    pass


class ResourceNotFoundError(BillingError):
    pass
