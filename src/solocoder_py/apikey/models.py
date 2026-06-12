from __future__ import annotations

import hashlib
import os
import secrets
import time
from dataclasses import dataclass, field
from typing import FrozenSet, List, Optional, Set


def _validate_scope_pattern(name: str) -> None:
    if not name:
        raise ValueError("scope name cannot be empty")
    if name == "*":
        return
    parts = name.split(":")
    for i, p in enumerate(parts):
        if p == "*" and i != len(parts) - 1:
            raise ValueError(
                f"wildcard '*' is only allowed at the end of a scope pattern, "
                f"got '{name}'"
            )
        if p == "":
            raise ValueError(
                f"scope pattern cannot contain empty segments, got '{name}'"
            )


def _match_scope_pattern(pattern: str, scope: str) -> bool:
    _validate_scope_pattern(pattern)
    if not scope:
        return False
    if pattern == "*":
        return True
    pattern_parts = pattern.split(":")
    scope_parts = scope.split(":")
    for i, p in enumerate(pattern_parts):
        if p == "*":
            return True
        if i >= len(scope_parts):
            return False
        if p != scope_parts[i]:
            return False
    return len(pattern_parts) <= len(scope_parts)


@dataclass(frozen=True)
class Scope:
    name: str

    def __post_init__(self) -> None:
        _validate_scope_pattern(self.name)

    @classmethod
    def parse(cls, spec: str) -> "Scope":
        if not spec:
            raise ValueError("scope spec cannot be empty")
        return cls(name=spec)

    def matches(self, scope: str) -> bool:
        return _match_scope_pattern(self.name, scope)

    def __str__(self) -> str:
        return self.name


class ScopeRegistry:
    _scopes: Set[str]
    _implications: dict[str, Set[str]]

    def __init__(self) -> None:
        self._scopes = set()
        self._implications = {}

    def register_scope(self, scope: str, implies: Optional[List[str]] = None) -> None:
        if not scope:
            raise ValueError("scope cannot be empty")
        Scope(name=scope)
        if implies:
            for imp in implies:
                Scope(name=imp)
        self._scopes.add(scope)
        if scope not in self._implications:
            self._implications[scope] = set()
        if implies:
            for imp in implies:
                self._implications[scope].add(imp)

    def get_effective_scopes(self, scopes: Set[str]) -> Set[str]:
        effective: Set[str] = set()
        stack = list(scopes)
        while stack:
            current = stack.pop()
            if current in effective:
                continue
            effective.add(current)
            if current in self._implications:
                stack.extend(self._implications[current])
        return effective

    def has_scope(self, granted_scopes: Set[str], required_scope: str) -> bool:
        effective = self.get_effective_scopes(granted_scopes)
        for granted in effective:
            scope_obj = Scope(name=granted)
            if scope_obj.matches(required_scope):
                return True
        return False


@dataclass
class UsageStats:
    total_uses: int = 0
    last_used_at: Optional[float] = None
    window_uses: int = 0
    is_idle: bool = False
    idle_days: float = 0.0


@dataclass
class APIKey:
    key_id: str
    subject: str
    scopes: FrozenSet[str]
    prefix: str
    created_at: float
    revoked: bool = False
    revoked_at: Optional[float] = None

    def __post_init__(self) -> None:
        if not self.key_id:
            raise ValueError("key_id cannot be empty")
        if not self.subject:
            raise ValueError("subject cannot be empty")
        if not self.prefix:
            raise ValueError("prefix cannot be empty")


@dataclass
class APIKeyCreateResult:
    key_id: str
    subject: str
    scopes: FrozenSet[str]
    key_secret: str
    prefix: str
    created_at: float

    def __post_init__(self) -> None:
        if not self.key_id:
            raise ValueError("key_id cannot be empty")
        if not self.subject:
            raise ValueError("subject cannot be empty")
        if not self.key_secret:
            raise ValueError("key_secret cannot be empty")
        if not self.prefix:
            raise ValueError("prefix cannot be empty")


@dataclass
class APIKeyInfo:
    key_id: str
    subject: str
    scopes: FrozenSet[str]
    prefix: str
    created_at: float
    revoked: bool
    revoked_at: Optional[float]
    usage: UsageStats

    def __post_init__(self) -> None:
        if not self.key_id:
            raise ValueError("key_id cannot be empty")
        if not self.subject:
            raise ValueError("subject cannot be empty")
        if not self.prefix:
            raise ValueError("prefix cannot be empty")


class Clock:
    def now(self) -> float:
        return time.time()

    def monotonic(self) -> float:
        return time.monotonic()


def generate_key_secret(length: int = 48) -> str:
    if length < 32:
        raise ValueError("key length must be at least 32 characters")
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def generate_key_id() -> str:
    return "k_" + secrets.token_hex(12)


def hash_key_secret(key_secret: str) -> str:
    return hashlib.sha256(key_secret.encode("utf-8")).hexdigest()


def get_key_prefix(key_secret: str, length: int = 8) -> str:
    if length <= 0:
        raise ValueError("prefix length must be positive")
    if length > len(key_secret):
        raise ValueError("prefix length cannot exceed key length")
    return key_secret[:length]
