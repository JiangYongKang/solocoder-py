from __future__ import annotations

import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Generator, List, Optional, Tuple

from .exceptions import (
    AccountExistsError,
    AccountNotFoundError,
    DuplicatePostError,
    OverdraftError,
    TransactionBalanceError,
    TransactionStateError,
)
from .models import (
    Account,
    AccountType,
    Entry,
    EntryType,
    Transaction,
    TransactionStatus,
    make_entry,
    make_transaction,
)


@dataclass
class Ledger:
    _accounts: Dict[str, Account] = field(default_factory=dict)
    _transactions: Dict[str, Transaction] = field(default_factory=dict)
    _account_entries: Dict[str, List[Entry]] = field(default_factory=dict)
    _account_locks: Dict[str, threading.RLock] = field(default_factory=dict)
    _global_lock: threading.RLock = field(default_factory=threading.RLock)
    _next_transaction_seq: int = 1

    def _get_or_create_account_lock(self, account_id: str) -> threading.RLock:
        with self._global_lock:
            if account_id not in self._account_locks:
                self._account_locks[account_id] = threading.RLock()
            return self._account_locks[account_id]

    @contextmanager
    def _lock_accounts(self, account_ids: List[str]) -> Generator[None, None, None]:
        sorted_ids = sorted(set(account_ids))
        locks = [self._get_or_create_account_lock(aid) for aid in sorted_ids]
        acquired: List[threading.RLock] = []
        try:
            for lock in locks:
                lock.acquire()
                acquired.append(lock)
            yield
        finally:
            for lock in reversed(acquired):
                lock.release()

    def _snapshot_account_ids(self) -> List[str]:
        with self._global_lock:
            return sorted(self._accounts.keys())

    def create_account(
        self,
        account_id: str,
        name: str,
        account_type: AccountType = AccountType.ASSET,
        allow_overdraft: bool = False,
        initial_balance: int = 0,
    ) -> Account:
        if not account_id:
            raise ValueError("account_id cannot be empty")
        if not name:
            raise ValueError("name cannot be empty")
        if initial_balance < 0 and not allow_overdraft:
            raise OverdraftError(
                f"Cannot create account {account_id} with negative initial balance "
                f"without overdraft enabled"
            )

        with self._global_lock:
            if account_id in self._accounts:
                raise AccountExistsError(f"Account {account_id} already exists")

            account = Account(
                account_id=account_id,
                name=name,
                account_type=account_type,
                allow_overdraft=allow_overdraft,
                balance=initial_balance,
            )
            self._accounts[account_id] = account
            self._account_entries[account_id] = []
            return account

    def get_account(self, account_id: str) -> Account:
        with self._global_lock:
            if account_id not in self._accounts:
                raise AccountNotFoundError(f"Account {account_id} not found")
            return self._accounts[account_id]

    def get_balance(self, account_id: str) -> int:
        account = self.get_account(account_id)
        lock = self._get_or_create_account_lock(account_id)
        with lock:
            return account.balance

    def list_accounts(self) -> List[Account]:
        with self._global_lock:
            return list(self._accounts.values())

    def get_account_entries(
        self,
        account_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        status: Optional[TransactionStatus] = None,
    ) -> List[Tuple[Entry, Transaction]]:
        self.get_account(account_id)

        with self._global_lock:
            entries = list(self._account_entries.get(account_id, []))
            transactions = dict(self._transactions)

        results: List[Tuple[Entry, Transaction]] = []
        for entry in entries:
            txn = transactions.get(self._find_transaction_for_entry(entry, transactions))
            if txn is None:
                continue
            if status is not None and txn.status != status:
                continue
            if start_time is not None and txn.created_at < start_time:
                continue
            if end_time is not None and txn.created_at > end_time:
                continue
            results.append((entry, txn))
        return results

    def _find_transaction_for_entry(
        self, entry: Entry, transactions: Dict[str, Transaction]
    ) -> str:
        for txn_id, txn in transactions.items():
            for e in txn.entries:
                if e.entry_id == entry.entry_id:
                    return txn_id
        return ""

    def create_transaction(
        self,
        debit_account_id: str,
        credit_account_id: str,
        amount: int,
        description: str = "",
    ) -> Transaction:
        if debit_account_id == credit_account_id:
            raise ValueError("debit and credit accounts must be different")
        if amount < 0:
            raise ValueError("amount cannot be negative")

        self.get_account(debit_account_id)
        self.get_account(credit_account_id)

        debit_entry = make_entry(
            account_id=debit_account_id,
            entry_type=EntryType.DEBIT,
            amount=amount,
            description=description,
        )
        credit_entry = make_entry(
            account_id=credit_account_id,
            entry_type=EntryType.CREDIT,
            amount=amount,
            description=description,
        )
        txn = make_transaction(
            entries=[debit_entry, credit_entry],
            description=description,
        )

        with self._global_lock:
            self._transactions[txn.transaction_id] = txn
            for entry in txn.entries:
                self._account_entries.setdefault(entry.account_id, []).append(entry)
        return txn

    def create_multi_entry_transaction(
        self,
        entries: List[Tuple[str, EntryType, int, str]],
        description: str = "",
    ) -> Transaction:
        account_ids = {e[0] for e in entries}
        for aid in account_ids:
            self.get_account(aid)

        txn_entries = [
            make_entry(
                account_id=aid,
                entry_type=etype,
                amount=amount,
                description=desc,
            )
            for aid, etype, amount, desc in entries
        ]
        txn = make_transaction(entries=txn_entries, description=description)

        with self._global_lock:
            self._transactions[txn.transaction_id] = txn
            for entry in txn.entries:
                self._account_entries.setdefault(entry.account_id, []).append(entry)
        return txn

    def get_transaction(self, transaction_id: str) -> Transaction:
        with self._global_lock:
            if transaction_id not in self._transactions:
                raise ValueError(f"Transaction {transaction_id} not found")
            return self._transactions[transaction_id]

    def post_transaction(self, transaction_id: str) -> Transaction:
        with self._global_lock:
            txn = self._transactions.get(transaction_id)
            if txn is None:
                raise ValueError(f"Transaction {transaction_id} not found")

            if txn.is_posted:
                raise DuplicatePostError(
                    f"Transaction {transaction_id} is already posted"
                )
            if not txn.is_draft:
                raise TransactionStateError(
                    f"Cannot post transaction in state {txn.status}"
                )

            if not txn.has_debit():
                raise TransactionBalanceError(
                    "Transaction must have at least one debit entry"
                )
            if not txn.has_credit():
                raise TransactionBalanceError(
                    "Transaction must have at least one credit entry"
                )
            if not txn.is_balanced:
                raise TransactionBalanceError(
                    f"Debit total ({txn.total_debit}) does not equal "
                    f"credit total ({txn.total_credit})"
                )

            account_ids = list(txn.get_account_ids())
            for aid in account_ids:
                if aid not in self._accounts:
                    raise AccountNotFoundError(f"Account {aid} not found")

        with self._lock_accounts(account_ids):
            if txn.is_posted:
                raise DuplicatePostError(
                    f"Transaction {transaction_id} is already posted"
                )

            for entry in txn.entries:
                account = self._accounts[entry.account_id]
                if entry.entry_type == EntryType.CREDIT:
                    if not account.can_credit(entry.amount):
                        raise OverdraftError(
                            f"Insufficient balance in account {account.account_id}: "
                            f"balance={account.balance}, credit amount={entry.amount}"
                        )

            applied_entries: List[Tuple[Entry, Account, int]] = []
            try:
                for entry in txn.entries:
                    account = self._accounts[entry.account_id]
                    prev_balance = account.balance
                    if entry.entry_type == EntryType.DEBIT:
                        account.apply_debit(entry.amount)
                    else:
                        account.apply_credit(entry.amount)
                    applied_entries.append((entry, account, prev_balance))
            except OverdraftError:
                for entry, account, prev_balance in reversed(applied_entries):
                    account.balance = prev_balance
                raise

            txn.mark_posted()
            return txn

    def transfer(
        self,
        debit_account_id: str,
        credit_account_id: str,
        amount: int,
        description: str = "",
    ) -> Transaction:
        txn = self.create_transaction(
            debit_account_id=debit_account_id,
            credit_account_id=credit_account_id,
            amount=amount,
            description=description,
        )
        return self.post_transaction(txn.transaction_id)

    def get_all_balances(self) -> Dict[str, int]:
        account_ids = self._snapshot_account_ids()
        balances: Dict[str, int] = {}

        with self._lock_accounts(account_ids):
            for aid in account_ids:
                account = self._accounts.get(aid)
                if account is not None:
                    balances[aid] = account.balance
        return balances

    def get_trial_balance(self) -> Tuple[int, int, bool]:
        total_debits = 0
        total_credits = 0

        with self._global_lock:
            for txn in self._transactions.values():
                if not txn.is_posted:
                    continue
                for entry in txn.entries:
                    if entry.entry_type == EntryType.DEBIT:
                        total_debits += entry.amount
                    else:
                        total_credits += entry.amount

        return total_debits, total_credits, total_debits == total_credits

    def list_transactions(
        self,
        status: Optional[TransactionStatus] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Transaction]:
        results: List[Transaction] = []
        with self._global_lock:
            for txn in self._transactions.values():
                if status is not None and txn.status != status:
                    continue
                if start_time is not None and txn.created_at < start_time:
                    continue
                if end_time is not None and txn.created_at > end_time:
                    continue
                results.append(txn)
        return results
