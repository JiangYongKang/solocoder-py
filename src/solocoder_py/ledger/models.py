from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import uuid4

from .exceptions import (
    EntryValidationError,
    OverdraftError,
    TransactionStateError,
)


class EntryType(str, Enum):
    DEBIT = "debit"
    CREDIT = "credit"


class TransactionStatus(str, Enum):
    DRAFT = "draft"
    POSTED = "posted"


class AccountType(str, Enum):
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    REVENUE = "revenue"
    EXPENSE = "expense"


@dataclass
class Account:
    account_id: str
    name: str
    account_type: AccountType = AccountType.ASSET
    allow_overdraft: bool = False
    balance: int = 0
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if not self.account_id:
            raise ValueError("account_id cannot be empty")
        if not self.name:
            raise ValueError("name cannot be empty")
        if self.balance < 0 and not self.allow_overdraft:
            raise OverdraftError(
                f"Account {self.account_id} does not allow overdraft"
            )

    def can_credit(self, amount: int) -> bool:
        if amount < 0:
            return False
        if self.allow_overdraft:
            return True
        return self.balance >= amount

    def apply_debit(self, amount: int) -> None:
        if amount < 0:
            raise EntryValidationError("Amount cannot be negative")
        self.balance += amount

    def apply_credit(self, amount: int) -> None:
        if amount < 0:
            raise EntryValidationError("Amount cannot be negative")
        if not self.can_credit(amount):
            raise OverdraftError(
                f"Insufficient balance in account {self.account_id}: "
                f"balance={self.balance}, credit amount={amount}"
            )
        self.balance -= amount


@dataclass
class Entry:
    entry_id: str
    account_id: str
    entry_type: EntryType
    amount: int
    description: str = ""

    def __post_init__(self) -> None:
        if not self.entry_id:
            raise ValueError("entry_id cannot be empty")
        if not self.account_id:
            raise ValueError("account_id cannot be empty")
        if self.amount < 0:
            raise EntryValidationError("Amount cannot be negative")


@dataclass
class Transaction:
    transaction_id: str
    entries: List[Entry]
    description: str = ""
    status: TransactionStatus = TransactionStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.now)
    posted_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if not self.transaction_id:
            raise ValueError("transaction_id cannot be empty")
        if not self.entries:
            raise EntryValidationError("Transaction must have at least one entry")
        for entry in self.entries:
            if entry.amount < 0:
                raise EntryValidationError("Entry amount cannot be negative")

    @property
    def is_draft(self) -> bool:
        return self.status == TransactionStatus.DRAFT

    @property
    def is_posted(self) -> bool:
        return self.status == TransactionStatus.POSTED

    @property
    def total_debit(self) -> int:
        return sum(e.amount for e in self.entries if e.entry_type == EntryType.DEBIT)

    @property
    def total_credit(self) -> int:
        return sum(e.amount for e in self.entries if e.entry_type == EntryType.CREDIT)

    @property
    def is_balanced(self) -> bool:
        return self.total_debit == self.total_credit

    def has_debit(self) -> bool:
        return any(e.entry_type == EntryType.DEBIT for e in self.entries)

    def has_credit(self) -> bool:
        return any(e.entry_type == EntryType.CREDIT for e in self.entries)

    def mark_posted(self) -> None:
        if not self.is_draft:
            raise TransactionStateError(
                f"Cannot post transaction in state {self.status}"
            )
        self.status = TransactionStatus.POSTED
        self.posted_at = datetime.now()

    def get_account_ids(self) -> set[str]:
        return {e.account_id for e in self.entries}


def make_entry(account_id: str, entry_type: EntryType, amount: int, description: str = "") -> Entry:
    return Entry(
        entry_id=str(uuid4()),
        account_id=account_id,
        entry_type=entry_type,
        amount=amount,
        description=description,
    )


def make_transaction(entries: List[Entry], description: str = "") -> Transaction:
    return Transaction(
        transaction_id=str(uuid4()),
        entries=entries,
        description=description,
    )
