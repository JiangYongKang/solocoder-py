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
    TransactionNotFoundError,
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
    _entry_to_transaction: Dict[str, str] = field(default_factory=dict)
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
                initial_balance=initial_balance,
            )
            self._accounts[account_id] = account
            self._account_entries[account_id] = []
            return account.copy()

    def get_account(self, account_id: str) -> Account:
        with self._global_lock:
            if account_id not in self._accounts:
                raise AccountNotFoundError(f"Account {account_id} not found")
            return self._accounts[account_id].copy()

    def get_balance(self, account_id: str) -> int:
        with self._global_lock:
            if account_id not in self._accounts:
                raise AccountNotFoundError(f"Account {account_id} not found")
            return self._accounts[account_id].balance

    def list_accounts(self) -> List[Account]:
        with self._global_lock:
            return [a.copy() for a in self._accounts.values()]

    def get_account_entries(
        self,
        account_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        status: Optional[TransactionStatus] = None,
    ) -> List[Tuple[Entry, Transaction]]:
        self.get_account(account_id)

        with self._global_lock:
            entries = [e.copy() for e in self._account_entries.get(account_id, [])]
            results: List[Tuple[Entry, Transaction]] = []
            for entry in entries:
                txn_id = self._entry_to_transaction.get(entry.entry_id)
                if txn_id is None:
                    continue
                txn = self._transactions.get(txn_id)
                if txn is None:
                    continue
                if status is not None and txn.status != status:
                    continue
                if start_time is not None and txn.created_at < start_time:
                    continue
                if end_time is not None and txn.created_at > end_time:
                    continue
                results.append((entry, txn.copy()))
        return results

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
                self._entry_to_transaction[entry.entry_id] = txn.transaction_id
        return txn.copy()

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
                self._entry_to_transaction[entry.entry_id] = txn.transaction_id
        return txn.copy()

    def get_transaction(self, transaction_id: str) -> Transaction:
        with self._global_lock:
            if transaction_id not in self._transactions:
                raise TransactionNotFoundError(
                    f"Transaction {transaction_id} not found"
                )
            return self._transactions[transaction_id].copy()

    def post_transaction(self, transaction_id: str) -> Transaction:
        with self._global_lock:
            txn = self._transactions.get(transaction_id)
            if txn is None:
                raise TransactionNotFoundError(
                    f"Transaction {transaction_id} not found"
                )

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
            return txn.copy()

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

    def get_trial_balance(
        self,
    ) -> Tuple[int, int, bool, Dict[str, Tuple[int, int, int, int, bool]]]:
        account_details: Dict[str, Tuple[int, int, int, int, bool]] = {}

        with self._global_lock:
            account_entries: Dict[str, List[Entry]] = {
                aid: list(es) for aid, es in self._account_entries.items()
            }
            transactions = dict(self._transactions)
            accounts = {aid: a.copy() for aid, a in self._accounts.items()}

        total_debit_balances = 0
        total_credit_balances = 0

        for account_id, account in accounts.items():
            total_debits = 0
            total_credits = 0
            for entry in account_entries.get(account_id, []):
                txn_id = self._entry_to_transaction.get(entry.entry_id)
                if txn_id is None:
                    continue
                txn = transactions.get(txn_id)
                if txn is None or not txn.is_posted:
                    continue
                if entry.entry_type == EntryType.DEBIT:
                    total_debits += entry.amount
                else:
                    total_credits += entry.amount

            expected_balance = account.initial_balance + total_debits - total_credits
            integrity_ok = expected_balance == account.balance

            account_details[account_id] = (
                total_debits,
                total_credits,
                account.balance,
                expected_balance,
                integrity_ok,
            )

            if account.balance > 0:
                total_debit_balances += account.balance
            elif account.balance < 0:
                total_credit_balances += abs(account.balance)

        balanced = total_debit_balances == total_credit_balances and all(
            d[4] for d in account_details.values()
        )

        return total_debit_balances, total_credit_balances, balanced, account_details

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
                results.append(txn.copy())
        return results
