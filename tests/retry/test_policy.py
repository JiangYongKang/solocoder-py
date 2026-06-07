from __future__ import annotations

import pytest

from solocoder_py.retry import (
    CompositePolicy,
    ErrorCodePolicy,
    ExceptionTypePolicy,
    RetryAllPolicy,
    RetryNonePolicy,
)


class CustomError(Exception):
    pass


class SubCustomError(CustomError):
    pass


class AnotherError(Exception):
    pass


class ErrorWithCode(CustomError):
    def __init__(self, code: str, message: str = "") -> None:
        self.code = code
        super().__init__(message)


class TestRetryAllPolicy:
    def test_retry_all_returns_true_for_all_exceptions(self):
        policy = RetryAllPolicy()
        assert policy.is_retryable(Exception("test"))
        assert policy.is_retryable(ValueError("value"))
        assert policy.is_retryable(CustomError("custom"))


class TestRetryNonePolicy:
    def test_retry_none_returns_false_for_all_exceptions(self):
        policy = RetryNonePolicy()
        assert not policy.is_retryable(Exception("test"))
        assert not policy.is_retryable(ValueError("value"))


class TestExceptionTypePolicy:
    def test_default_retryable_only_checks_non_retryable(self):
        policy = ExceptionTypePolicy(
            non_retryable_exceptions=[ValueError]
        )
        assert policy.is_retryable(KeyError("key"))
        assert not policy.is_retryable(ValueError("value"))
        assert policy.is_retryable(CustomError("custom"))

    def test_explicit_retryable_types(self):
        policy = ExceptionTypePolicy(
            retryable_exceptions=[ValueError, KeyError]
        )
        assert policy.is_retryable(ValueError("value"))
        assert policy.is_retryable(KeyError("key"))
        assert not policy.is_retryable(CustomError("custom"))
        assert not policy.is_retryable(TypeError("type"))

    def test_subclass_matching(self):
        policy = ExceptionTypePolicy(
            retryable_exceptions=[CustomError]
        )
        assert policy.is_retryable(CustomError("custom"))
        assert policy.is_retryable(SubCustomError("sub"))
        assert not policy.is_retryable(AnotherError("another"))

    def test_non_retryable_overrides_retryable(self):
        policy = ExceptionTypePolicy(
            retryable_exceptions=[CustomError],
            non_retryable_exceptions=[SubCustomError],
        )
        assert policy.is_retryable(CustomError("custom"))
        assert not policy.is_retryable(SubCustomError("sub"))

    def test_empty_policy_retry_all(self):
        policy = ExceptionTypePolicy()
        assert policy.is_retryable(Exception("anything"))

    def test_retryable_types_property(self):
        policy = ExceptionTypePolicy(retryable_exceptions=[ValueError, KeyError])
        assert ValueError in policy.retryable_types
        assert KeyError in policy.retryable_types

    def test_non_retryable_types_property(self):
        policy = ExceptionTypePolicy(non_retryable_exceptions=[ValueError])
        assert ValueError in policy.non_retryable_types


class TestErrorCodePolicy:
    def test_default_no_codes_allows_all(self):
        policy = ErrorCodePolicy()
        assert policy.is_retryable(Exception("no code"))
        assert policy.is_retryable(ErrorWithCode("ERR_001"))

    def test_retryable_codes_whitelist(self):
        policy = ErrorCodePolicy(
            retryable_codes=["TIMEOUT", "RATE_LIMITED"]
        )
        assert policy.is_retryable(ErrorWithCode("TIMEOUT"))
        assert policy.is_retryable(ErrorWithCode("RATE_LIMITED"))
        assert not policy.is_retryable(ErrorWithCode("BAD_REQUEST"))

    def test_non_retryable_codes_blacklist(self):
        policy = ErrorCodePolicy(
            non_retryable_codes=["BAD_REQUEST", "NOT_FOUND"]
        )
        assert not policy.is_retryable(ErrorWithCode("BAD_REQUEST"))
        assert not policy.is_retryable(ErrorWithCode("NOT_FOUND"))
        assert policy.is_retryable(ErrorWithCode("TIMEOUT"))

    def test_non_retryable_overrides_retryable(self):
        policy = ErrorCodePolicy(
            retryable_codes=["TIMEOUT", "RATE_LIMITED"],
            non_retryable_codes=["TIMEOUT_FATAL"],
        )
        assert policy.is_retryable(ErrorWithCode("TIMEOUT"))
        assert not policy.is_retryable(ErrorWithCode("TIMEOUT_FATAL"))

    def test_no_code_attribute_allows_retry(self):
        policy = ErrorCodePolicy(retryable_codes=["TIMEOUT"])
        assert policy.is_retryable(Exception("no code attr"))

    def test_code_converted_to_string(self):
        class IntCodeError(Exception):
            def __init__(self, code: int) -> None:
                self.code = code
                super().__init__()

        policy = ErrorCodePolicy(retryable_codes=["500"])
        assert policy.is_retryable(IntCodeError(500))
        assert not policy.is_retryable(IntCodeError(400))

    def test_custom_code_attribute(self):
        class StatusError(Exception):
            def __init__(self, status: str) -> None:
                self.status = status
                super().__init__()

        policy = ErrorCodePolicy(
            retryable_codes=["503"],
            code_attribute="status",
        )
        assert policy.is_retryable(StatusError("503"))
        assert not policy.is_retryable(StatusError("400"))

    def test_retryable_codes_property(self):
        policy = ErrorCodePolicy(retryable_codes=["A", "B"])
        assert policy.retryable_codes == {"A", "B"}

    def test_non_retryable_codes_property(self):
        policy = ErrorCodePolicy(non_retryable_codes=["X"])
        assert policy.non_retryable_codes == {"X"}


class TestCompositePolicy:
    def test_empty_composite_allows_all(self):
        policy = CompositePolicy([])
        assert policy.is_retryable(Exception("test"))

    def test_all_policies_must_allow(self):
        p1 = ExceptionTypePolicy(retryable_exceptions=[CustomError])
        p2 = ErrorCodePolicy(non_retryable_codes=["FATAL"])
        policy = CompositePolicy([p1, p2])

        assert policy.is_retryable(ErrorWithCode("TIMEOUT"))
        assert not policy.is_retryable(ErrorWithCode("FATAL"))
        assert not policy.is_retryable(AnotherError("another"))

    def test_policies_property(self):
        p1 = RetryAllPolicy()
        p2 = RetryAllPolicy()
        policy = CompositePolicy([p1, p2])
        assert len(policy.policies) == 2
