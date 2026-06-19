from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol

from .exceptions import (
    AccountLockedError,
    BackoffActiveError,
    CaptchaInvalidError,
    CaptchaRequiredError,
    InvalidAccountError,
    InvalidIPError,
    LoginRateError,
)


@dataclass(frozen=True)
class LoginRateConfig:
    account_lock_threshold: int = 5
    subnet_captcha_threshold: int = 10
    initial_backoff_seconds: int = 1
    max_backoff_seconds: int = 300
    backoff_multiplier: int = 2

    def __post_init__(self) -> None:
        if self.account_lock_threshold <= 0:
            raise ValueError("account_lock_threshold must be positive")
        if self.subnet_captcha_threshold <= 0:
            raise ValueError("subnet_captcha_threshold must be positive")
        if self.initial_backoff_seconds <= 0:
            raise ValueError("initial_backoff_seconds must be positive")
        if self.max_backoff_seconds <= 0:
            raise ValueError("max_backoff_seconds must be positive")
        if self.initial_backoff_seconds > self.max_backoff_seconds:
            raise ValueError("initial_backoff_seconds cannot exceed max_backoff_seconds")
        if self.backoff_multiplier <= 1:
            raise ValueError("backoff_multiplier must be greater than 1")


@dataclass
class AccountState:
    failure_count: int = 0
    last_failure_time: Optional[float] = None
    is_locked: bool = False
    locked_at: Optional[float] = None

    def reset(self) -> None:
        self.failure_count = 0
        self.last_failure_time = None
        self.is_locked = False
        self.locked_at = None


@dataclass
class SubnetState:
    failure_count: int = 0
    last_failure_time: Optional[float] = None

    def reset(self) -> None:
        self.failure_count = 0
        self.last_failure_time = None


class CaptchaVerifier(Protocol):
    def verify(self, account: str, ip: str, captcha_solution: str) -> bool:
        ...


class DefaultCaptchaVerifier:
    def verify(self, account: str, ip: str, captcha_solution: str) -> bool:
        return False


@dataclass
class LoginAttemptResult:
    success: bool
    account_failures: int
    subnet_failures: int
    error: Optional[LoginRateError] = None


@dataclass
class LoginRateManagerState:
    account_states: dict[str, AccountState] = field(default_factory=dict)
    subnet_states: dict[str, SubnetState] = field(default_factory=dict)
