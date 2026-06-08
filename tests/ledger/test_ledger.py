from __future__ import annotations

import threading
import time
from datetime import datetime

import pytest

from solocoder_py.ledger import (
    Account,
    AccountExistsError,
    AccountNotFoundError,
    AccountType,
    DuplicatePostError,
    Entry,
    EntryType,
    Ledger,
    OverdraftError,
    Transaction,
    TransactionBalanceError,
    TransactionStatus,
    make_entry,
    make_transaction,
)
from .conftest import make_ledger


def _add_raw_transaction(ledger: Ledger, txn: Transaction) -> None:
    ledger._transactions[txn.transaction_id] = txn
    for e in txn.entries:
        ledger._account_entries.setdefault(e.account_id, []).append(e)


class TestAccountModel:
    def test_account_creation_defaults(self):
        account = Account(account_id="acc-1", name="Cash")
        assert account.account_id == "acc-1"
        assert account.name == "Cash"
        assert account.account_type == AccountType.ASSET
        assert account.allow_overdraft is False
        assert account.balance == 0

    def test_account_with_balance(self):
        account = Account(account_id="acc-1", name="Cash", balance=1000)
        assert account.balance == 1000

    def test_account_overdraft_disallowed(self):
        with pytest.raises(OverdraftError):
            Account(
                account_id="acc-1",
                name="Cash",
                allow_overdraft=False,
                balance=-100,
            )

    def test_account_overdraft_allowed(self):
        account = Account(
            account_id="acc-1",
            name="Credit Line",
            allow_overdraft=True,
            balance=-500,
        )
        assert account.balance == -500

    def test_account_empty_id_raises(self):
        with pytest.raises(ValueError, match="account_id cannot be empty"):
            Account(account_id="", name="Cash")

    def test_account_empty_name_raises(self):
        with pytest.raises(ValueError, match="name cannot be empty"):
            Account(account_id="acc-1", name="")

    def test_can_credit_sufficient_balance(self):
        account = Account(account_id="acc-1", name="Cash", balance=500)
        assert account.can_credit(300) is True

    def test_can_credit_insufficient_balance(self):
        account = Account(account_id="acc-1", name="Cash", balance=100)
        assert account.can_credit(200) is False

    def test_can_credit_negative_amount(self):
        account = Account(account_id="acc-1", name="Cash", balance=500)
        assert account.can_credit(-1) is False

    def test_can_credit_with_overdraft(self):
        account = Account(
            account_id="acc-1", name="Cash", balance=100, allow_overdraft=True
        )
        assert account.can_credit(500) is True

    def test_apply_debit_increases_balance(self):
        account = Account(account_id="acc-1", name="Cash", balance=500)
        account.apply_debit(300)
        assert account.balance == 800

    def test_apply_credit_decreases_balance(self):
        account = Account(account_id="acc-1", name="Cash", balance=500)
        account.apply_credit(300)
        assert account.balance == 200

    def test_apply_credit_overdraft(self):
        account = Account(account_id="acc-1", name="Cash", balance=100)
        with pytest.raises(OverdraftError):
            account.apply_credit(200)


class TestEntryModel:
    def test_entry_creation(self):
        entry = Entry(
            entry_id="e-1",
            account_id="acc-1",
            entry_type=EntryType.DEBIT,
            amount=100,
        )
        assert entry.entry_id == "e-1"
        assert entry.account_id == "acc-1"
        assert entry.entry_type == EntryType.DEBIT
        assert entry.amount == 100

    def test_entry_negative_amount_raises(self):
        with pytest.raises(Exception):
            Entry(
                entry_id="e-1",
                account_id="acc-1",
                entry_type=EntryType.DEBIT,
                amount=-1,
            )


class TestTransactionModel:
    def test_transaction_creation(self):
        debit = make_entry("acc-1", EntryType.DEBIT, 100)
        credit = make_entry("acc-2", EntryType.CREDIT, 100)
        txn = make_transaction([debit, credit], "test")
        assert txn.is_draft is True
        assert txn.is_posted is False
        assert txn.is_balanced is True
        assert txn.total_debit == 100
        assert txn.total_credit == 100

    def test_transaction_unbalanced(self):
        debit = make_entry("acc-1", EntryType.DEBIT, 100)
        credit = make_entry("acc-2", EntryType.CREDIT, 50)
        txn = make_transaction([debit, credit])
        assert txn.is_balanced is False
        assert txn.total_debit == 100
        assert txn.total_credit == 50

    def test_transaction_empty_entries_raises(self):
        with pytest.raises(Exception):
            make_transaction([])

    def test_transaction_mark_posted(self):
        debit = make_entry("acc-1", EntryType.DEBIT, 100)
        credit = make_entry("acc-2", EntryType.CREDIT, 100)
        txn = make_transaction([debit, credit])
        txn.mark_posted()
        assert txn.is_posted is True
        assert txn.is_draft is False
        assert txn.posted_at is not None

    def test_transaction_mark_posted_twice_raises(self):
        debit = make_entry("acc-1", EntryType.DEBIT, 100)
        credit = make_entry("acc-2", EntryType.CREDIT, 100)
        txn = make_transaction([debit, credit])
        txn.mark_posted()
        with pytest.raises(Exception):
            txn.mark_posted()

    def test_transaction_get_account_ids(self):
        entries = [
            make_entry("acc-1", EntryType.DEBIT, 50),
            make_entry("acc-2", EntryType.CREDIT, 30),
            make_entry("acc-3", EntryType.CREDIT, 20),
        ]
        txn = make_transaction(entries)
        assert txn.get_account_ids() == {"acc-1", "acc-2", "acc-3"}

    def test_transaction_no_debit(self):
        credit = make_entry("acc-1", EntryType.CREDIT, 100)
        txn = make_transaction([credit])
        assert txn.has_debit() is False
        assert txn.has_credit() is True

    def test_transaction_no_credit(self):
        debit = make_entry("acc-1", EntryType.DEBIT, 100)
        txn = make_transaction([debit])
        assert txn.has_debit() is True
        assert txn.has_credit() is False


class TestAccountCreation:
    def test_create_account(self):
        ledger = make_ledger()
        account = ledger.create_account("cash", "Cash Account")
        assert account.account_id == "cash"
        assert account.name == "Cash Account"
        assert account.balance == 0
        assert ledger.get_balance("cash") == 0

    def test_create_account_with_initial_balance(self):
        ledger = make_ledger()
        account = ledger.create_account(
            "cash", "Cash Account", initial_balance=1000
        )
        assert account.balance == 1000
        assert ledger.get_balance("cash") == 1000

    def test_create_duplicate_account_raises(self):
        ledger = make_ledger()
        ledger.create_account("cash", "Cash")
        with pytest.raises(AccountExistsError):
            ledger.create_account("cash", "Cash 2")

    def test_create_account_negative_balance_without_overdraft_raises(self):
        ledger = make_ledger()
        with pytest.raises(OverdraftError):
            ledger.create_account(
                "cash", "Cash", allow_overdraft=False, initial_balance=-100
            )

    def test_create_account_negative_balance_with_overdraft(self):
        ledger = make_ledger()
        account = ledger.create_account(
            "credit", "Credit Line", allow_overdraft=True, initial_balance=-500
        )
        assert account.balance == -500

    def test_get_nonexistent_account_raises(self):
        ledger = make_ledger()
        with pytest.raises(AccountNotFoundError):
            ledger.get_account("nonexistent")

    def test_list_accounts(self):
        ledger = make_ledger()
        ledger.create_account("a", "Account A")
        ledger.create_account("b", "Account B")
        accounts = ledger.list_accounts()
        assert len(accounts) == 2
        account_ids = {a.account_id for a in accounts}
        assert account_ids == {"a", "b"}


class TestSinglePosting:
    def test_simple_transfer(self):
        ledger = make_ledger()
        ledger.create_account("cash", "Cash", initial_balance=1000)
        ledger.create_account("expense", "Expense")

        txn = ledger.transfer(
            debit_account_id="expense",
            credit_account_id="cash",
            amount=300,
            description="Office supplies",
        )

        assert txn.is_posted is True
        assert ledger.get_balance("cash") == 700
        assert ledger.get_balance("expense") == 300

    def test_zero_amount_transfer(self):
        ledger = make_ledger()
        ledger.create_account("a", "Account A", initial_balance=500)
        ledger.create_account("b", "Account B", initial_balance=200)

        txn = ledger.transfer("a", "b", 0)
        assert txn.is_posted is True
        assert ledger.get_balance("a") == 500
        assert ledger.get_balance("b") == 200

    def test_create_then_post_transaction(self):
        ledger = make_ledger()
        ledger.create_account("bank", "Bank", initial_balance=500)
        ledger.create_account("cash", "Cash")

        txn = ledger.create_transaction(
            debit_account_id="cash",
            credit_account_id="bank",
            amount=200,
        )
        assert txn.is_draft is True
        assert ledger.get_balance("bank") == 500
        assert ledger.get_balance("cash") == 0

        posted = ledger.post_transaction(txn.transaction_id)
        assert posted.is_posted is True
        assert ledger.get_balance("bank") == 300
        assert ledger.get_balance("cash") == 200


class TestMultiEntryTransaction:
    def test_multi_debit_multi_credit(self):
        ledger = make_ledger()
        ledger.create_account("cash", "Cash", initial_balance=1000)
        ledger.create_account("bank", "Bank", initial_balance=2000)
        ledger.create_account("rent", "Rent Expense")
        ledger.create_account("util", "Utility Expense")

        txn = ledger.create_multi_entry_transaction(
            entries=[
                ("rent", EntryType.DEBIT, 500, "Rent"),
                ("util", EntryType.DEBIT, 200, "Utilities"),
                ("cash", EntryType.CREDIT, 300, "Cash portion"),
                ("bank", EntryType.CREDIT, 400, "Bank portion"),
            ],
            description="Monthly bills",
        )
        ledger.post_transaction(txn.transaction_id)

        assert ledger.get_balance("cash") == 700
        assert ledger.get_balance("bank") == 1600
        assert ledger.get_balance("rent") == 500
        assert ledger.get_balance("util") == 200

    def test_complex_transaction_balanced(self):
        ledger = make_ledger()
        ledger.create_account("a", "A", initial_balance=1000)
        ledger.create_account("b", "B", initial_balance=500)
        ledger.create_account("c", "C")
        ledger.create_account("d", "D")
        ledger.create_account("e", "E")

        txn = ledger.create_multi_entry_transaction(
            entries=[
                ("a", EntryType.CREDIT, 100, ""),
                ("b", EntryType.CREDIT, 200, ""),
                ("c", EntryType.DEBIT, 150, ""),
                ("d", EntryType.DEBIT, 100, ""),
                ("e", EntryType.DEBIT, 50, ""),
            ]
        )
        assert txn.is_balanced is True
        assert txn.total_debit == 300
        assert txn.total_credit == 300

        ledger.post_transaction(txn.transaction_id)
        assert ledger.get_balance("a") == 900
        assert ledger.get_balance("b") == 300
        assert ledger.get_balance("c") == 150
        assert ledger.get_balance("d") == 100
        assert ledger.get_balance("e") == 50


class TestTransactionBalanceValidation:
    def test_post_unbalanced_transaction_raises(self):
        ledger = make_ledger()
        ledger.create_account("a", "A", initial_balance=500)
        ledger.create_account("b", "B", initial_balance=500)

        debit = make_entry("a", EntryType.DEBIT, 100)
        credit = make_entry("b", EntryType.CREDIT, 50)
        txn = make_transaction([debit, credit])
        _add_raw_transaction(ledger, txn)

        with pytest.raises(TransactionBalanceError):
            ledger.post_transaction(txn.transaction_id)

    def test_post_transaction_no_debit_raises(self):
        ledger = make_ledger()
        ledger.create_account("a", "A", initial_balance=500)

        credit = make_entry("a", EntryType.CREDIT, 100)
        txn = make_transaction([credit])
        _add_raw_transaction(ledger, txn)

        with pytest.raises(TransactionBalanceError):
            ledger.post_transaction(txn.transaction_id)

    def test_post_transaction_no_credit_raises(self):
        ledger = make_ledger()
        ledger.create_account("a", "A", initial_balance=500)

        debit = make_entry("a", EntryType.DEBIT, 100)
        txn = make_transaction([debit])
        _add_raw_transaction(ledger, txn)

        with pytest.raises(TransactionBalanceError):
            ledger.post_transaction(txn.transaction_id)


class TestDraftTransaction:
    def test_draft_transaction_does_not_affect_balance(self):
        ledger = make_ledger()
        ledger.create_account("cash", "Cash", initial_balance=1000)
        ledger.create_account("expense", "Expense")

        txn = ledger.create_transaction("expense", "cash", 300)
        assert txn.is_draft is True
        assert ledger.get_balance("cash") == 1000
        assert ledger.get_balance("expense") == 0

    def test_list_draft_vs_posted_transactions(self):
        ledger = make_ledger()
        ledger.create_account("a", "A", initial_balance=1000)
        ledger.create_account("b", "B", initial_balance=1000)

        txn1 = ledger.create_transaction("a", "b", 100)
        txn2 = ledger.create_transaction("a", "b", 200)
        ledger.post_transaction(txn2.transaction_id)

        drafts = ledger.list_transactions(status=TransactionStatus.DRAFT)
        posted = ledger.list_transactions(status=TransactionStatus.POSTED)

        assert len(drafts) == 1
        assert drafts[0].transaction_id == txn1.transaction_id
        assert len(posted) == 1
        assert posted[0].transaction_id == txn2.transaction_id


class TestDuplicatePost:
    def test_post_already_posted_transaction_raises(self):
        ledger = make_ledger()
        ledger.create_account("a", "A", initial_balance=500)
        ledger.create_account("b", "B", initial_balance=500)

        txn = ledger.transfer("a", "b", 100)
        assert txn.is_posted is True
        assert ledger.get_balance("a") == 600
        assert ledger.get_balance("b") == 400

        with pytest.raises(DuplicatePostError):
            ledger.post_transaction(txn.transaction_id)

        assert ledger.get_balance("a") == 600
        assert ledger.get_balance("b") == 400


class TestOverdraftValidation:
    def test_overdraft_rejected(self):
        ledger = make_ledger()
        ledger.create_account("cash", "Cash", initial_balance=100)
        ledger.create_account("expense", "Expense")

        with pytest.raises(OverdraftError):
            ledger.transfer("expense", "cash", 200)

        assert ledger.get_balance("cash") == 100
        assert ledger.get_balance("expense") == 0

    def test_overdraft_allowed_account(self):
        ledger = make_ledger()
        ledger.create_account(
            "credit", "Credit Line", allow_overdraft=True, initial_balance=0
        )
        ledger.create_account("expense", "Expense")

        txn = ledger.transfer("expense", "credit", 500)
        assert txn.is_posted is True
        assert ledger.get_balance("credit") == -500
        assert ledger.get_balance("expense") == 500

    def test_atomic_rollback_on_overdraft_in_multi_entry(self):
        ledger = make_ledger()
        ledger.create_account("a", "A", initial_balance=50)
        ledger.create_account("b", "B", initial_balance=1000)
        ledger.create_account("c", "C")
        ledger.create_account("d", "D")

        txn = ledger.create_multi_entry_transaction(
            entries=[
                ("c", EntryType.DEBIT, 100, ""),
                ("d", EntryType.DEBIT, 600, ""),
                ("a", EntryType.CREDIT, 100, ""),
                ("b", EntryType.CREDIT, 600, ""),
            ]
        )

        with pytest.raises(OverdraftError):
            ledger.post_transaction(txn.transaction_id)

        assert ledger.get_balance("a") == 50
        assert ledger.get_balance("b") == 1000
        assert ledger.get_balance("c") == 0
        assert ledger.get_balance("d") == 0


class TestTrialBalance:
    def test_trial_balance_empty(self):
        ledger = make_ledger()
        td, tc, balanced = ledger.get_trial_balance()
        assert td == 0
        assert tc == 0
        assert balanced is True

    def test_trial_balance_after_transfers(self):
        ledger = make_ledger()
        ledger.create_account("cash", "Cash", initial_balance=1000)
        ledger.create_account("bank", "Bank", initial_balance=2000)
        ledger.create_account("rent", "Rent Expense")
        ledger.create_account("salary", "Salary Expense")

        ledger.transfer("rent", "cash", 400)
        ledger.transfer("salary", "bank", 800)

        td, tc, balanced = ledger.get_trial_balance()
        assert balanced is True
        assert td == 1200
        assert tc == 1200

    def test_trial_balance_all_accounts_zero(self):
        ledger = make_ledger()
        ledger.create_account("a", "A", initial_balance=1000)
        ledger.create_account("b", "B", initial_balance=1000)
        ledger.create_account("c", "C", initial_balance=1000)

        ledger.transfer("a", "b", 100)
        ledger.transfer("b", "c", 100)
        ledger.transfer("c", "a", 100)

        assert ledger.get_balance("a") == 1000
        assert ledger.get_balance("b") == 1000
        assert ledger.get_balance("c") == 1000

        td, tc, balanced = ledger.get_trial_balance()
        assert balanced is True
        assert td == 300
        assert tc == 300


class TestGetAllBalances:
    def test_get_all_balances(self):
        ledger = make_ledger()
        ledger.create_account("a", "A", initial_balance=100)
        ledger.create_account("b", "B", initial_balance=200)
        ledger.create_account("c", "C", initial_balance=300)

        balances = ledger.get_all_balances()
        assert balances == {"a": 100, "b": 200, "c": 300}


class TestAccountEntriesHistory:
    def test_get_account_entries(self):
        ledger = make_ledger()
        ledger.create_account("cash", "Cash", initial_balance=1000)
        ledger.create_account("expense", "Expense")

        ledger.transfer("expense", "cash", 300, "Payment 1")
        ledger.transfer("expense", "cash", 200, "Payment 2")

        entries = ledger.get_account_entries("cash")
        assert len(entries) == 2
        for entry, txn in entries:
            assert entry.account_id == "cash"
            assert entry.entry_type == EntryType.CREDIT
            assert txn.is_posted is True

    def test_filter_entries_by_status(self):
        ledger = make_ledger()
        ledger.create_account("a", "A", initial_balance=1000)
        ledger.create_account("b", "B", initial_balance=1000)

        ledger.create_transaction("a", "b", 100)
        txn_posted = ledger.transfer("a", "b", 200)

        draft_entries = ledger.get_account_entries(
            "a", status=TransactionStatus.DRAFT
        )
        posted_entries = ledger.get_account_entries(
            "a", status=TransactionStatus.POSTED
        )

        assert len(draft_entries) == 1
        assert draft_entries[0][1].is_draft is True
        assert len(posted_entries) == 1
        assert posted_entries[0][1].transaction_id == txn_posted.transaction_id

    def test_filter_entries_by_time_range(self):
        ledger = make_ledger()
        ledger.create_account("a", "A", initial_balance=1000)
        ledger.create_account("b", "B", initial_balance=1000)

        before = datetime.now()
        time.sleep(0.01)
        ledger.transfer("a", "b", 100)
        time.sleep(0.01)
        middle = datetime.now()
        time.sleep(0.01)
        ledger.transfer("a", "b", 200)
        time.sleep(0.01)
        after = datetime.now()

        first_entries = ledger.get_account_entries("a", end_time=middle)
        assert len(first_entries) == 1

        second_entries = ledger.get_account_entries("a", start_time=middle)
        assert len(second_entries) == 1

        all_entries = ledger.get_account_entries("a", start_time=before, end_time=after)
        assert len(all_entries) == 2


class TestConcurrency:
    def test_concurrent_transfers_between_two_accounts(self):
        ledger = make_ledger()
        ledger.create_account("a", "A", initial_balance=10000)
        ledger.create_account("b", "B", initial_balance=10000)

        errors = []
        success_count = {"count": 0}
        lock = threading.Lock()

        def transfer_a_to_b(amount, times):
            for _ in range(times):
                try:
                    ledger.transfer("a", "b", amount)
                    with lock:
                        success_count["count"] += 1
                except Exception as e:
                    with lock:
                        errors.append(e)

        def transfer_b_to_a(amount, times):
            for _ in range(times):
                try:
                    ledger.transfer("b", "a", amount)
                    with lock:
                        success_count["count"] += 1
                except Exception as e:
                    with lock:
                        errors.append(e)

        threads = [
            threading.Thread(target=transfer_a_to_b, args=(10, 100)),
            threading.Thread(target=transfer_b_to_a, args=(10, 100)),
            threading.Thread(target=transfer_a_to_b, args=(5, 50)),
            threading.Thread(target=transfer_b_to_a, args=(5, 50)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15)
            assert t.is_alive() is False

        assert len(errors) == 0, f"Unexpected errors: {errors}"
        assert success_count["count"] == 300
        assert ledger.get_balance("a") + ledger.get_balance("b") == 20000

    def test_concurrent_transfers_no_deadlock(self):
        ledger = make_ledger()
        num_accounts = 5
        for i in range(num_accounts):
            ledger.create_account(f"acc-{i}", f"Account {i}", initial_balance=10000)

        errors = []
        lock = threading.Lock()

        def worker(tid, iterations):
            for i in range(iterations):
                src = f"acc-{(tid + i) % num_accounts}"
                dst = f"acc-{(tid + i + 1) % num_accounts}"
                try:
                    ledger.transfer(src, dst, 1)
                except Exception as e:
                    with lock:
                        errors.append(e)

        threads = [
            threading.Thread(target=worker, args=(tid, 50))
            for tid in range(5)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=20)
            assert t.is_alive() is False

        assert len(errors) == 0, f"Unexpected errors: {errors}"
        total = sum(ledger.get_balance(f"acc-{i}") for i in range(num_accounts))
        assert total == num_accounts * 10000

    def test_concurrent_balance_read_consistency(self):
        ledger = make_ledger()
        ledger.create_account("main", "Main", initial_balance=1000000)
        ledger.create_account("other", "Other", initial_balance=1000000)

        stop_flag = threading.Event()
        errors = []
        read_pairs = []
        lock = threading.Lock()

        def writer():
            try:
                while not stop_flag.is_set():
                    ledger.transfer("other", "main", 1)
                    ledger.transfer("main", "other", 1)
            except Exception as e:
                with lock:
                    errors.append(e)

        def reader():
            try:
                while not stop_flag.is_set():
                    balances = ledger.get_all_balances()
                    with lock:
                        read_pairs.append((balances["main"], balances["other"]))
            except Exception as e:
                with lock:
                    errors.append(e)

        writer_threads = [threading.Thread(target=writer) for _ in range(2)]
        reader_threads = [threading.Thread(target=reader) for _ in range(3)]

        for t in writer_threads + reader_threads:
            t.start()

        time.sleep(0.5)
        stop_flag.set()

        for t in writer_threads + reader_threads:
            t.join(timeout=10)
            assert t.is_alive() is False

        assert len(errors) == 0, f"Unexpected errors: {errors}"
        assert len(read_pairs) > 0
        for main_bal, other_bal in read_pairs:
            assert main_bal + other_bal == 2000000, (
                f"Money supply not conserved: main={main_bal}, other={other_bal}"
            )
            diff = abs(main_bal - 1000000)
            assert diff <= 2, (
                f"Balance drift too large: main={main_bal}, diff={diff}"
            )

    def test_concurrent_overdraft_consistency(self):
        ledger = make_ledger()
        ledger.create_account("cash", "Cash", initial_balance=100)
        ledger.create_account("expense", "Expense")

        overdraft_count = {"count": 0}
        success_count = {"count": 0}
        lock = threading.Lock()

        def try_withdraw():
            for _ in range(10):
                try:
                    ledger.transfer("expense", "cash", 30)
                    with lock:
                        success_count["count"] += 1
                except OverdraftError:
                    with lock:
                        overdraft_count["count"] += 1
                except Exception as e:
                    with lock:
                        overdraft_count["count"] += 0

        threads = [threading.Thread(target=try_withdraw) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
            assert t.is_alive() is False

        cash_balance = ledger.get_balance("cash")
        expense_balance = ledger.get_balance("expense")
        assert cash_balance >= 0
        assert cash_balance + expense_balance == 100
        assert success_count["count"] <= 3
        assert cash_balance == 100 - success_count["count"] * 30
