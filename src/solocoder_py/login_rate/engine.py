from __future__ import annotations

import ipaddress
import re
import threading
from typing import Callable, Optional

from ..ratelimiter.clock import Clock, SystemClock
from .exceptions import (
    AccountLockedError,
    BackoffActiveError,
    CaptchaInvalidError,
    CaptchaRequiredError,
    InvalidAccountError,
    InvalidIPError,
    NoSuchAccountCounterError,
    NoSuchSubnetCounterError,
)
from .models import (
    AccountState,
    CaptchaVerifier,
    DefaultCaptchaVerifier,
    LoginAttemptResult,
    LoginRateConfig,
    LoginRateManagerState,
    SubnetState,
)


_ACCOUNT_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{1,255}$")


def _validate_account(account: str) -> None:
    if not isinstance(account, str) or not account or not _ACCOUNT_PATTERN.match(account):
        raise InvalidAccountError(account)


def _validate_ip(ip: str) -> None:
    if not isinstance(ip, str) or not ip:
        raise InvalidIPError(ip)
    try:
        ipaddress.IPv4Address(ip)
    except (ipaddress.AddressValueError, ValueError):
        try:
            ipaddress.IPv6Address(ip)
        except (ipaddress.AddressValueError, ValueError):
            raise InvalidIPError(ip)


def _extract_subnet(ip: str) -> str:
    try:
        addr = ipaddress.IPv4Address(ip)
        network = ipaddress.IPv4Network(f"{ip}/24", strict=False)
        return str(network.network_address) + "/24"
    except (ipaddress.AddressValueError, ValueError):
        try:
            addr = ipaddress.IPv6Address(ip)
            network = ipaddress.IPv6Network(f"{ip}/64", strict=False)
            return str(network.network_address) + "/64"
        except (ipaddress.AddressValueError, ValueError):
            raise InvalidIPError(ip)


class LoginRateManager:
    def __init__(
        self,
        config: Optional[LoginRateConfig] = None,
        clock: Optional[Clock] = None,
        captcha_verifier: Optional[CaptchaVerifier] = None,
    ) -> None:
        self._config: LoginRateConfig = config or LoginRateConfig()
        self._clock: Clock = clock or SystemClock()
        self._captcha_verifier: CaptchaVerifier = captcha_verifier or DefaultCaptchaVerifier()
        self._state = LoginRateManagerState()
        self._account_locks: dict[str, threading.Lock] = {}
        self._subnet_locks: dict[str, threading.Lock] = {}
        self._struct_lock: threading.Lock = threading.Lock()

    @property
    def config(self) -> LoginRateConfig:
        return self._config

    def set_captcha_verifier(self, verifier: CaptchaVerifier) -> None:
        self._captcha_verifier = verifier

    def _get_account_lock(self, account: str) -> threading.Lock:
        with self._struct_lock:
            if account not in self._account_locks:
                self._account_locks[account] = threading.Lock()
            return self._account_locks[account]

    def _get_subnet_lock(self, subnet: str) -> threading.Lock:
        with self._struct_lock:
            if subnet not in self._subnet_locks:
                self._subnet_locks[subnet] = threading.Lock()
            return self._subnet_locks[subnet]

    def _get_or_create_account_state(self, account: str) -> AccountState:
        with self._struct_lock:
            if account not in self._state.account_states:
                self._state.account_states[account] = AccountState()
            return self._state.account_states[account]

    def _get_or_create_subnet_state(self, subnet: str) -> SubnetState:
        with self._struct_lock:
            if subnet not in self._state.subnet_states:
                self._state.subnet_states[subnet] = SubnetState()
            return self._state.subnet_states[subnet]

    def _calculate_backoff_seconds(self, failure_count: int) -> int:
        if failure_count <= 0:
            return 0
        exponent = failure_count - 1
        backoff = self._config.initial_backoff_seconds * (self._config.backoff_multiplier ** exponent)
        return min(backoff, self._config.max_backoff_seconds)

    def _get_remaining_backoff(self, state: AccountState, current_time: float) -> int:
        if state.failure_count <= 0 or state.last_failure_time is None:
            return 0
        required_backoff = self._calculate_backoff_seconds(state.failure_count)
        elapsed = current_time - state.last_failure_time
        remaining = required_backoff - elapsed
        return max(0, int(remaining + 0.999))

    def attempt_login(
        self,
        account: str,
        ip: str,
        password_verifier: Callable[[], bool],
        captcha_solution: Optional[str] = None,
    ) -> LoginAttemptResult:
        _validate_account(account)
        _validate_ip(ip)
        subnet = _extract_subnet(ip)

        current_time = self._clock.now()

        account_lock = self._get_account_lock(account)
        subnet_lock = self._get_subnet_lock(subnet)

        with account_lock:
            with subnet_lock:
                account_state = self._get_or_create_account_state(account)
                subnet_state = self._get_or_create_subnet_state(subnet)

                captcha_passed = False
                if subnet_state.failure_count >= self._config.subnet_captcha_threshold:
                    if captcha_solution is None:
                        return LoginAttemptResult(
                            success=False,
                            account_failures=account_state.failure_count,
                            subnet_failures=subnet_state.failure_count,
                            error=CaptchaRequiredError(subnet),
                        )
                    if not self._captcha_verifier.verify(account, ip, captcha_solution):
                        return LoginAttemptResult(
                            success=False,
                            account_failures=account_state.failure_count,
                            subnet_failures=subnet_state.failure_count,
                            error=CaptchaInvalidError(),
                        )
                    captcha_passed = True

                if account_state.is_locked and not captcha_passed:
                    return LoginAttemptResult(
                        success=False,
                        account_failures=account_state.failure_count,
                        subnet_failures=subnet_state.failure_count,
                        error=AccountLockedError(account),
                    )

                remaining_backoff = self._get_remaining_backoff(account_state, current_time)
                if remaining_backoff > 0 and not captcha_passed:
                    return LoginAttemptResult(
                        success=False,
                        account_failures=account_state.failure_count,
                        subnet_failures=subnet_state.failure_count,
                        error=BackoffActiveError(remaining_backoff),
                    )

                password_ok = password_verifier()

                if password_ok:
                    account_state.reset()
                    subnet_state.reset()
                    return LoginAttemptResult(
                        success=True,
                        account_failures=0,
                        subnet_failures=0,
                        error=None,
                    )
                else:
                    account_state.failure_count += 1
                    account_state.last_failure_time = current_time
                    subnet_state.failure_count += 1
                    subnet_state.last_failure_time = current_time

                    if account_state.failure_count >= self._config.account_lock_threshold:
                        account_state.is_locked = True
                        account_state.locked_at = current_time

                    return LoginAttemptResult(
                        success=False,
                        account_failures=account_state.failure_count,
                        subnet_failures=subnet_state.failure_count,
                        error=None,
                    )

    def unlock_account(self, account: str) -> None:
        _validate_account(account)
        account_lock = self._get_account_lock(account)
        with account_lock:
            if account not in self._state.account_states:
                raise NoSuchAccountCounterError(account)
            state = self._state.account_states[account]
            state.is_locked = False
            state.locked_at = None
            state.failure_count = 0
            state.last_failure_time = None

    def get_account_failure_count(self, account: str) -> int:
        _validate_account(account)
        with self._struct_lock:
            if account not in self._state.account_states:
                raise NoSuchAccountCounterError(account)
            return self._state.account_states[account].failure_count

    def get_subnet_failure_count(self, subnet: str) -> int:
        with self._struct_lock:
            if subnet not in self._state.subnet_states:
                raise NoSuchSubnetCounterError(subnet)
            return self._state.subnet_states[subnet].failure_count

    def is_account_locked(self, account: str) -> bool:
        _validate_account(account)
        with self._struct_lock:
            if account not in self._state.account_states:
                raise NoSuchAccountCounterError(account)
            return self._state.account_states[account].is_locked

    def reset_account(self, account: str) -> None:
        _validate_account(account)
        account_lock = self._get_account_lock(account)
        with account_lock:
            if account in self._state.account_states:
                self._state.account_states[account].reset()

    def reset_subnet(self, subnet: str) -> None:
        with self._struct_lock:
            if subnet in self._state.subnet_states:
                self._state.subnet_states[subnet].reset()

    def reset_all(self) -> None:
        with self._struct_lock:
            self._state.account_states.clear()
            self._state.subnet_states.clear()

    def has_account_counter(self, account: str) -> bool:
        _validate_account(account)
        with self._struct_lock:
            return account in self._state.account_states

    def has_subnet_counter(self, subnet: str) -> bool:
        with self._struct_lock:
            return subnet in self._state.subnet_states

    def get_backoff_seconds(self, account: str) -> int:
        _validate_account(account)
        current_time = self._clock.now()
        account_lock = self._get_account_lock(account)
        with account_lock:
            if account not in self._state.account_states:
                return 0
            return self._get_remaining_backoff(self._state.account_states[account], current_time)

    def calculate_backoff_for_failures(self, failure_count: int) -> int:
        return self._calculate_backoff_seconds(failure_count)
