from __future__ import annotations


class LoginRateError(Exception):
    pass


class InvalidAccountError(LoginRateError):
    def __init__(self, account: str) -> None:
        self.account = account
        super().__init__(f"Invalid account: {account}")


class InvalidIPError(LoginRateError):
    def __init__(self, ip: str) -> None:
        self.ip = ip
        super().__init__(f"Invalid IP address: {ip}")


class AccountLockedError(LoginRateError):
    def __init__(self, account: str) -> None:
        self.account = account
        super().__init__(f"Account '{account}' is locked")


class BackoffActiveError(LoginRateError):
    def __init__(self, remaining_seconds: int) -> None:
        self.remaining_seconds = remaining_seconds
        super().__init__(f"Please wait {remaining_seconds} seconds before retrying")


class CaptchaRequiredError(LoginRateError):
    def __init__(self, subnet: str) -> None:
        self.subnet = subnet
        super().__init__(f"CAPTCHA verification required for subnet {subnet}")


class CaptchaInvalidError(LoginRateError):
    def __init__(self) -> None:
        super().__init__("CAPTCHA verification failed")


class NoSuchAccountCounterError(LoginRateError):
    def __init__(self, account: str) -> None:
        self.account = account
        super().__init__(f"No counter exists for account: {account}")


class NoSuchSubnetCounterError(LoginRateError):
    def __init__(self, subnet: str) -> None:
        self.subnet = subnet
        super().__init__(f"No counter exists for subnet: {subnet}")
