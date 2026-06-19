from __future__ import annotations


class LoginRateError(Exception):
    pass


class InvalidAccountError(LoginRateError):
    def __init__(self, account: str) -> None:
        self.account = account
        super().__init__(f"无效的账户名: {account}")


class InvalidIPError(LoginRateError):
    def __init__(self, ip: str) -> None:
        self.ip = ip
        super().__init__(f"无效的 IP 地址: {ip}")


class AccountLockedError(LoginRateError):
    def __init__(self, account: str) -> None:
        self.account = account
        super().__init__(f"账户已锁定")


class BackoffActiveError(LoginRateError):
    def __init__(self, remaining_seconds: int) -> None:
        self.remaining_seconds = remaining_seconds
        super().__init__(f"请等待 {remaining_seconds} 秒后重试")


class CaptchaRequiredError(LoginRateError):
    def __init__(self, subnet: str) -> None:
        self.subnet = subnet
        super().__init__(f"需要进行 CAPTCHA 验证")


class CaptchaInvalidError(LoginRateError):
    def __init__(self) -> None:
        super().__init__("CAPTCHA 验证失败")


class NoSuchAccountCounterError(LoginRateError):
    def __init__(self, account: str) -> None:
        self.account = account
        super().__init__(f"不存在该账户的计数器: {account}")


class NoSuchSubnetCounterError(LoginRateError):
    def __init__(self, subnet: str) -> None:
        self.subnet = subnet
        super().__init__(f"不存在该子网的计数器: {subnet}")
