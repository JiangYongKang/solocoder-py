from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from .models import HashResult


@dataclass
class UserCredentials:
    username: str
    stored_hash: HashResult


@dataclass
class InMemoryHashStore:
    hash_records: Dict[str, HashResult] = field(default_factory=dict)
    user_credentials: Dict[str, UserCredentials] = field(default_factory=dict)

    def store_hash(self, key: str, hash_result: HashResult) -> None:
        self.hash_records[key] = hash_result

    def get_hash(self, key: str) -> Optional[HashResult]:
        return self.hash_records.get(key)

    def delete_hash(self, key: str) -> bool:
        if key in self.hash_records:
            del self.hash_records[key]
            return True
        return False

    def store_user_credentials(self, username: str, hash_result: HashResult) -> None:
        self.user_credentials[username] = UserCredentials(
            username=username,
            stored_hash=hash_result,
        )

    def get_user_credentials(self, username: str) -> Optional[UserCredentials]:
        return self.user_credentials.get(username)

    def update_user_credentials(self, username: str, new_hash: HashResult) -> bool:
        if username in self.user_credentials:
            self.user_credentials[username].stored_hash = new_hash
            return True
        return False

    def delete_user_credentials(self, username: str) -> bool:
        if username in self.user_credentials:
            del self.user_credentials[username]
            return True
        return False

    def clear(self) -> None:
        self.hash_records.clear()
        self.user_credentials.clear()

    def __len__(self) -> int:
        return len(self.hash_records) + len(self.user_credentials)
