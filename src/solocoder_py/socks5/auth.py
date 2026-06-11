from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List

from .constants import AUTH_NO_AUTH, AUTH_USERNAME_PASSWORD


class AuthProvider(ABC):
    @abstractmethod
    def get_supported_methods(self) -> List[int]:
        ...

    @abstractmethod
    def authenticate(self, username: str, password: str) -> bool:
        ...


class NoAuthAuthProvider(AuthProvider):
    def get_supported_methods(self) -> List[int]:
        return [AUTH_NO_AUTH]

    def authenticate(self, username: str, password: str) -> bool:
        return True


class InMemoryAuthProvider(AuthProvider):
    def __init__(self, credentials: Dict[str, str]) -> None:
        self._credentials = dict(credentials)

    def get_supported_methods(self) -> List[int]:
        if self._credentials:
            return [AUTH_NO_AUTH, AUTH_USERNAME_PASSWORD]
        return [AUTH_NO_AUTH]

    def authenticate(self, username: str, password: str) -> bool:
        if username in self._credentials:
            return self._credentials[username] == password
        return False
