from datetime import datetime, timedelta

import pytest

from solocoder_py.reconciliation import (
    DiscrepancyType,
    MatchType,
    ReconciliationEngine,
    ReconciliationError,
    ToleranceConfig,
    Transaction,
    TransactionSide,
    TransactionStatus,
    normalize_channel_record,
    normalize_internal_record,
)

from .conftest import make_channel_record, make_internal_record


class TestTransactionImport:
    def test_import_internal_transactions(self, default_engine, base_time):
        records = [
            make_internal_record("T001", 100.0, base_time),
            make_internal_record("T002", 200.5, base_time + timedelta(minutes=1)),
        ]
        imported = default_engine.import_internal_transactions(records)
        assert len(imported) == 2
        assert default_engine.get_internal_transaction("T001") is not None
        assert default_engine.get_internal_transaction("T002").amount == 200.5

    def test_import_channel_transactions(self, default_engine, base_time):
        records = [
            make_channel_record("T001", 100.0, base_time),
            make_channel_record("T002", 200.5, base_time + timedelta(minutes=1)),
        ]
        imported = default_engine.import_channel_transactions(records)
        assert len(imported) == 2
        assert default_engine.get_channel_transaction("T001") is not None
        assert default_engine.get_channel_transaction("T001").side == TransactionSide.CHANNEL

    def test_duplicate_transactions_dedup_on_import(self, default_engine, base_time):
        records = [
            make_internal_record("T001", 100.0, base_time),
            make_internal_record("T001", 999.0, base_time),
        ]
        imported = default_engine.import_internal_transactions(records)
        assert len(imported) == 1
        assert default_engine.get_internal_transaction("T001").amount == 100.0

    def test_import_idempotent(self, default_engine, base_time):
        records = [make_internal_record("T001", 100.0, base_time)]
        default_engine.import_internal_transactions(records)
        imported_again = default_engine.import_internal_transactions(records)
        assert len(imported_again) == 0

    def test_normalize_internal_different_field_names(self):
        rec = {
            "transaction_id": "TX-001",
            "amount": "150.75",
            "pay_time": "2024-06-01T12:00:00",
            "status": "success",
            "order_id": "ORD-100",
        }
        txn = normalize_internal_record(rec)
        assert txn.txn_id == "TX-001"
        assert txn.amount == 150.75
        assert txn.txn_time == datetime(2024, 6, 1, 12, 0, 0)
        assert txn.status == TransactionStatus.SUCCESS
        assert txn.order_id == "ORD-100"

    def test_normalize_channel_different_field_names(self):
        rec = {
            "trade_no": "CH-001",
            "amount": "250.50",
            "paid_at": "2024-06-01T14:30:00",
            "status": "success",
            "out_trade_no": "ORD-200",
        }
        txn = normalize_channel_record(rec)
        assert txn.txn_id == "CH-001"
        assert txn.amount == 250.5
        assert txn.txn_time == datetime(2024, 6, 1, 14, 30, 0)
        assert txn.order_id == "ORD-200"
        assert txn.side == TransactionSide.CHANNEL

    def test_list_transactions(self, default_engine, base_time):
        default_engine.import_internal_transactions([
            make_internal_record("T001", 100.0, base_time),
            make_internal_record("T002", 200.0, base_time),
        ])
        default_engine.import_channel_transactions([
            make_channel_record("C001", 100.0, base_time),
        ])
        assert len(default_engine.list_internal_transactions()) == 2
        assert len(default_engine.list_channel_transactions()) == 1

    def test_clear_engine(self, default_engine, base_time):
        default_engine.import_internal_transactions([
            make_internal_record("T001", 100.0, base_time),
        ])
        default_engine.import_channel_transactions([
            make_channel_record("T001", 100.0, base_time),
        ])
        default_engine.clear()
        assert len(default_engine.list_internal_transactions()) == 0
        assert len(default_engine.list_channel_transactions()) == 0


class TestExactMatch:
    def test_full_exact_match_by_id(self, default_engine, base_time):
        default_engine.import_internal_transactions([
            make_internal_record("T001", 100.0, base_time),
            make_internal_record("T002", 200.0, base_time),
        ])
        default_engine.import_channel_transactions([
            make_channel_record("T001", 100.0, base_time),
            make_channel_record("T002", 200.0, base_time),
        ])
        report = default_engine.reconcile()
        assert report.matched_count == 2
        assert report.matched_amount == 300.0
        assert report.internal_discrepancy_total_count == 0
        assert report.channel_discrepancy_total_count == 0
        for pair in report.matched_pairs:
            assert pair.match_type == MatchType.EXACT
            assert pair.diff_amount == 0.0
            assert pair.write_off is False

    def test_generate_report_summary(self, default_engine, base_time):
        default_engine.import_internal_transactions([
            make_internal_record("T001", 100.0, base_time),
        ])
        default_engine.import_channel_transactions([
            make_channel_record("T001", 100.0, base_time),
        ])
        report = default_engine.reconcile()
        summary = report.summary()
        assert summary["internal_total"]["count"] == 1
        assert summary["channel_total"]["count"] == 1
        assert summary["matched"]["count"] == 1
        assert "batch_id" in summary
        assert "start_time" in summary


class TestToleranceWriteOff:
    def test_within_absolute_tolerance_write_off(self, lenient_engine, base_time):
        lenient_engine.import_internal_transactions([
            make_internal_record("T001", 100.0, base_time),
        ])
        lenient_engine.import_channel_transactions([
            make_channel_record("T001", 99.5, base_time),
        ])
        report = lenient_engine.reconcile()
        assert report.matched_count == 1
        assert report.tolerance_write_off_count == 1
        assert report.tolerance_write_off_diff_amount == 0.5
        pair = report.matched_pairs[0]
        assert pair.match_type == MatchType.TOLERANCE
        assert pair.write_off is True
        assert pair.diff_amount == 0.5

    def test_within_relative_tolerance_write_off(self, default_engine, base_time):
        default_engine.import_internal_transactions([
            make_internal_record("T001", 10000.0, base_time),
        ])
        default_engine.import_channel_transactions([
            make_channel_record("T001", 10000.5, base_time),
        ])
        report = default_engine.reconcile()
        assert report.matched_count == 1
        assert report.tolerance_write_off_count == 1

    def test_amount_diff_at_boundary_absolute_tolerance(self, default_engine, base_time):
        default_engine.import_internal_transactions([
            make_internal_record("T001", 100.0, base_time),
        ])
        default_engine.import_channel_transactions([
            make_channel_record("T001", 100.01, base_time),
        ])
        report = default_engine.reconcile()
        assert report.matched_count == 1
        assert report.tolerance_write_off_count == 1


class TestBoundaryConditions:
    def test_both_sides_empty(self, default_engine):
        report = default_engine.reconcile()
        assert report.internal_total_count == 0
        assert report.channel_total_count == 0
        assert report.matched_count == 0
        assert report.internal_discrepancy_total_count == 0
        assert report.channel_discrepancy_total_count == 0

    def test_internal_only_empty_channel(self, default_engine, base_time):
        default_engine.import_internal_transactions([
            make_internal_record("T001", 100.0, base_time),
            make_internal_record("T002", 200.0, base_time),
        ])
        report = default_engine.reconcile()
        assert report.internal_total_count == 2
        assert report.channel_total_count == 0
        assert report.matched_count == 0
        assert len(report.internal_discrepancies[DiscrepancyType.CHANNEL_MISSING]) == 2
        assert report.internal_discrepancy_total_amount == 300.0

    def test_channel_only_empty_internal(self, default_engine, base_time):
        default_engine.import_channel_transactions([
            make_channel_record("T001", 100.0, base_time),
        ])
        report = default_engine.reconcile()
        assert report.internal_total_count == 0
        assert report.channel_total_count == 1
        assert len(report.channel_discrepancies[DiscrepancyType.INTERNAL_MISSING]) == 1

    def test_large_number_all_matched(self, default_engine, base_time):
        count = 1000
        internal_records = []
        channel_records = []
        for i in range(count):
            internal_records.append(
                make_internal_record(f"T{i:04d}", float(i), base_time + timedelta(seconds=i))
            )
            channel_records.append(
                make_channel_record(f"T{i:04d}", float(i), base_time + timedelta(seconds=i))
            )
        default_engine.import_internal_transactions(internal_records)
        default_engine.import_channel_transactions(channel_records)
        report = default_engine.reconcile()
        assert report.matched_count == count
        assert report.internal_discrepancy_total_count == 0
        assert report.channel_discrepancy_total_count == 0

    def test_amount_diff_exactly_at_absolute_tolerance(self, base_time):
        tol = ToleranceConfig(absolute_tolerance=0.01)
        engine = ReconciliationEngine(tolerance=tol)
        engine.import_internal_transactions([
            make_internal_record("T001", 100.0, base_time),
        ])
        engine.import_channel_transactions([
            make_channel_record("T001", 100.01, base_time),
        ])
        report = engine.reconcile()
        assert report.matched_count == 1
        assert report.tolerance_write_off_count == 1


class TestDiscrepancyClassification:
    def test_channel_missing_discrepancy(self, default_engine, base_time):
        default_engine.import_internal_transactions([
            make_internal_record("T001", 100.0, base_time),
        ])
        default_engine.import_channel_transactions([])
        report = default_engine.reconcile()
        discrepancies = report.internal_discrepancies[DiscrepancyType.CHANNEL_MISSING]
        assert len(discrepancies) == 1
        assert discrepancies[0].internal_txn is not None
        assert discrepancies[0].internal_txn.txn_id == "T001"
        assert "No matching channel" in discrepancies[0].detail

    def test_internal_missing_discrepancy(self, default_engine, base_time):
        default_engine.import_internal_transactions([])
        default_engine.import_channel_transactions([
            make_channel_record("T001", 100.0, base_time),
        ])
        report = default_engine.reconcile()
        discrepancies = report.channel_discrepancies[DiscrepancyType.INTERNAL_MISSING]
        assert len(discrepancies) == 1
        assert discrepancies[0].channel_txn is not None

    def test_amount_mismatch_out_of_tolerance(self, strict_engine, base_time):
        strict_engine.import_internal_transactions([
            make_internal_record("T001", 100.0, base_time),
        ])
        strict_engine.import_channel_transactions([
            make_channel_record("T001", 150.0, base_time),
        ])
        report = strict_engine.reconcile()
        assert len(report.internal_discrepancies[DiscrepancyType.AMOUNT_MISMATCH]) == 1
        assert len(report.channel_discrepancies[DiscrepancyType.AMOUNT_MISMATCH]) == 1
        internal_disc = report.internal_discrepancies[DiscrepancyType.AMOUNT_MISMATCH][0]
        assert internal_disc.internal_txn is not None
        assert internal_disc.channel_txn is not None
        assert "Amount mismatch out of tolerance" in internal_disc.detail

    def test_status_mismatch_discrepancy(self, default_engine, base_time):
        default_engine.import_internal_transactions([
            make_internal_record("T001", 100.0, base_time, status="success"),
        ])
        default_engine.import_channel_transactions([
            make_channel_record("T001", 100.0, base_time, status="failed"),
        ])
        report = default_engine.reconcile()
        assert len(report.internal_discrepancies[DiscrepancyType.STATUS_MISMATCH]) == 1
        assert len(report.channel_discrepancies[DiscrepancyType.STATUS_MISMATCH]) == 1
        status_disc = report.internal_discrepancies[DiscrepancyType.STATUS_MISMATCH][0]
        assert "Status mismatch" in status_disc.detail
        assert "success" in status_disc.detail
        assert "failed" in status_disc.detail


class TestFallbackMatch:
    def test_fallback_match_by_amount_and_time(self, default_engine, base_time):
        default_engine.import_internal_transactions([
            make_internal_record("INT-001", 123.45, base_time),
        ])
        default_engine.import_channel_transactions([
            make_channel_record("CH-001", 123.45, base_time + timedelta(minutes=2)),
        ])
        report = default_engine.reconcile()
        assert report.matched_count == 1
        assert report.matched_pairs[0].match_type == MatchType.FALLBACK

    def test_fallback_match_outside_time_window(self, default_engine, base_time):
        default_engine.import_internal_transactions([
            make_internal_record("INT-001", 123.45, base_time),
        ])
        default_engine.import_channel_transactions([
            make_channel_record("CH-001", 123.45, base_time + timedelta(minutes=10)),
        ])
        report = default_engine.reconcile()
        assert report.matched_count == 0
        assert len(report.internal_discrepancies[DiscrepancyType.CHANNEL_MISSING]) == 1
        assert len(report.channel_discrepancies[DiscrepancyType.INTERNAL_MISSING]) == 1

    def test_fallback_match_with_tolerance_write_off(self, lenient_engine, base_time):
        lenient_engine.import_internal_transactions([
            make_internal_record("INT-001", 123.45, base_time),
        ])
        lenient_engine.import_channel_transactions([
            make_channel_record("CH-001", 123.00, base_time + timedelta(minutes=1)),
        ])
        report = lenient_engine.reconcile()
        assert report.matched_count == 1
        assert report.matched_pairs[0].match_type == MatchType.FALLBACK
        assert report.matched_pairs[0].write_off is True
        assert report.tolerance_write_off_count == 1


class TestReportsAndQuery:
    def test_get_report_by_batch_id(self, default_engine, base_time):
        default_engine.import_internal_transactions([
            make_internal_record("T001", 100.0, base_time),
        ])
        default_engine.import_channel_transactions([
            make_channel_record("T001", 100.0, base_time),
        ])
        report = default_engine.reconcile()
        fetched = default_engine.get_report(report.batch_id)
        assert fetched is not None
        assert fetched.batch_id == report.batch_id

    def test_list_reports(self, default_engine, base_time):
        default_engine.import_internal_transactions([
            make_internal_record("T001", 100.0, base_time),
        ])
        default_engine.import_channel_transactions([
            make_channel_record("T001", 100.0, base_time),
        ])
        r1 = default_engine.reconcile()
        r2 = default_engine.reconcile()
        reports = default_engine.list_reports()
        assert len(reports) == 2
        assert reports[0].batch_id == r1.batch_id
        assert reports[1].batch_id == r2.batch_id

    def test_query_reports_by_time_range(self, default_engine, base_time):
        default_engine.import_internal_transactions([
            make_internal_record("T001", 100.0, base_time),
        ])
        default_engine.import_channel_transactions([
            make_channel_record("T001", 100.0, base_time),
        ])
        r1 = default_engine.reconcile()
        r2_start = datetime.now() - timedelta(hours=1)
        r2_end = datetime.now() + timedelta(hours=1)
        results = default_engine.query_reports(start=r2_start, end=r2_end)
        assert len(results) >= 1
        assert any(r.batch_id == r1.batch_id for r in results)


class TestToleranceConfig:
    def test_absolute_tolerance(self):
        tol = ToleranceConfig(absolute_tolerance=0.05)
        assert tol.is_within_tolerance(100.0, 100.03) is True
        assert tol.is_within_tolerance(100.0, 100.06) is False

    def test_relative_tolerance(self):
        tol = ToleranceConfig(absolute_tolerance=0.0, relative_tolerance=0.001)
        assert tol.is_within_tolerance(1000.0, 1000.5) is True
        assert tol.is_within_tolerance(1000.0, 1002.0) is False

    def test_zero_amounts(self):
        tol = ToleranceConfig()
        assert tol.is_within_tolerance(0.0, 0.0) is True

    def test_diff_amount(self):
        tol = ToleranceConfig()
        assert tol.diff_amount(100.5, 100.0) == 0.5
        assert tol.diff_amount(99.0, 100.0) == -1.0


class TestTransactionValidation:
    def test_none_txn_id_is_allowed(self, base_time):
        txn = Transaction(
            txn_id=None,
            amount=100.0,
            txn_time=base_time,
            status=TransactionStatus.SUCCESS,
            side=TransactionSide.INTERNAL,
        )
        assert txn.txn_id is None
        assert txn.has_txn_id is False

    def test_empty_string_txn_id_is_allowed(self, base_time):
        txn = Transaction(
            txn_id="",
            amount=100.0,
            txn_time=base_time,
            status=TransactionStatus.SUCCESS,
            side=TransactionSide.INTERNAL,
        )
        assert txn.txn_id == ""
        assert txn.has_txn_id is False

    def test_negative_amount_raises(self, base_time):
        with pytest.raises(ReconciliationError):
            Transaction(
                txn_id="T001",
                amount=-10.0,
                txn_time=base_time,
                status=TransactionStatus.SUCCESS,
                side=TransactionSide.INTERNAL,
            )


class TestReconcileWithTimeWindow:
    def test_reconcile_filtered_by_time_window(self, default_engine, base_time):
        t1 = base_time
        t2 = base_time + timedelta(hours=2)
        default_engine.import_internal_transactions([
            make_internal_record("T001", 100.0, t1),
            make_internal_record("T002", 200.0, t2),
        ])
        default_engine.import_channel_transactions([
            make_channel_record("T001", 100.0, t1),
            make_channel_record("T002", 200.0, t2),
        ])
        window = (t1 - timedelta(minutes=1), t1 + timedelta(minutes=1))
        report = default_engine.reconcile(time_window=window)
        assert report.internal_total_count == 1
        assert report.channel_total_count == 1
        assert report.matched_count == 1


class TestDiscrepancyAmount:
    def test_discrepancy_amount_from_internal(self, base_time):
        from solocoder_py.reconciliation import Discrepancy
        txn = Transaction(
            txn_id="T001",
            amount=123.45,
            txn_time=base_time,
            status=TransactionStatus.SUCCESS,
            side=TransactionSide.INTERNAL,
        )
        d = Discrepancy.create(
            DiscrepancyType.CHANNEL_MISSING,
            internal_txn=txn,
        )
        assert d.amount == 123.45

    def test_discrepancy_amount_from_channel(self, base_time):
        txn = Transaction(
            txn_id="T001",
            amount=67.89,
            txn_time=base_time,
            status=TransactionStatus.SUCCESS,
            side=TransactionSide.CHANNEL,
        )
        from solocoder_py.reconciliation import Discrepancy
        d = Discrepancy.create(
            DiscrepancyType.INTERNAL_MISSING,
            channel_txn=txn,
        )
        assert d.amount == 67.89


class TestMixedScenarios:
    def test_mixed_matched_and_discrepancies(self, default_engine, base_time):
        default_engine.import_internal_transactions([
            make_internal_record("T001", 100.0, base_time),
            make_internal_record("T002", 200.0, base_time),
            make_internal_record("T003", 300.0, base_time),
            make_internal_record("T004", 400.0, base_time),
        ])
        default_engine.import_channel_transactions([
            make_channel_record("T001", 100.0, base_time),
            make_channel_record("T002", 999.0, base_time),
            make_channel_record("T003", 300.0, base_time, status="failed"),
            make_channel_record("T005", 500.0, base_time),
        ])
        report = default_engine.reconcile()
        assert report.internal_total_count == 4
        assert report.channel_total_count == 4
        assert report.matched_count == 1
        assert len(report.internal_discrepancies[DiscrepancyType.AMOUNT_MISMATCH]) == 1
        assert len(report.internal_discrepancies[DiscrepancyType.STATUS_MISMATCH]) == 1
        assert len(report.internal_discrepancies[DiscrepancyType.CHANNEL_MISSING]) == 1
        assert len(report.channel_discrepancies[DiscrepancyType.INTERNAL_MISSING]) == 1
        assert len(report.channel_discrepancies[DiscrepancyType.AMOUNT_MISMATCH]) == 1
        assert len(report.channel_discrepancies[DiscrepancyType.STATUS_MISMATCH]) == 1

    def test_report_totals(self, default_engine, base_time):
        default_engine.import_internal_transactions([
            make_internal_record("T001", 100.0, base_time),
            make_internal_record("T002", 200.0, base_time),
        ])
        default_engine.import_channel_transactions([
            make_channel_record("T001", 100.0, base_time),
            make_channel_record("T002", 200.0, base_time),
        ])
        report = default_engine.reconcile()
        assert report.internal_total_amount == 300.0
        assert report.channel_total_amount == 300.0
        assert report.matched_amount == 300.0
        assert report.internal_discrepancy_total_amount == 0
        assert report.channel_discrepancy_total_amount == 0


class TestMissingTxnIdFallback:
    def test_both_sides_missing_txn_id_match_via_fallback(self, default_engine, base_time):
        internal_records = [
            {"amount": 150.0, "txn_time": base_time, "status": "success"},
        ]
        channel_records = [
            {"amount": 150.0, "trade_time": base_time, "status": "success"},
        ]
        default_engine.import_internal_transactions(internal_records)
        default_engine.import_channel_transactions(channel_records)

        itxns = default_engine.list_internal_transactions()
        ctxns = default_engine.list_channel_transactions()
        assert len(itxns) == 1
        assert len(ctxns) == 1
        assert itxns[0].has_txn_id is False
        assert ctxns[0].has_txn_id is False

        report = default_engine.reconcile()
        assert report.matched_count == 1
        assert report.matched_pairs[0].match_type == MatchType.FALLBACK
        assert report.internal_discrepancy_total_count == 0
        assert report.channel_discrepancy_total_count == 0

    def test_multiple_missing_txn_id_not_falsely_deduped(self, default_engine, base_time):
        internal_records = [
            {"amount": 100.0, "txn_time": base_time, "status": "success"},
            {"amount": 200.0, "txn_time": base_time + timedelta(minutes=1), "status": "success"},
        ]
        channel_records = [
            {"amount": 100.0, "trade_time": base_time, "status": "success"},
            {"amount": 200.0, "trade_time": base_time + timedelta(minutes=1), "status": "success"},
        ]
        default_engine.import_internal_transactions(internal_records)
        default_engine.import_channel_transactions(channel_records)
        assert len(default_engine.list_internal_transactions()) == 2
        assert len(default_engine.list_channel_transactions()) == 2
        report = default_engine.reconcile()
        assert report.matched_count == 2
        assert report.internal_discrepancy_total_count == 0


class TestFallbackAmountPrecision:
    def test_fallback_amount_minor_float_precision_diff(self, default_engine, base_time):
        internal_records = [
            {"amount": 12.345000001, "txn_time": base_time, "status": "success"},
        ]
        channel_records = [
            {"amount": 12.345, "trade_time": base_time, "status": "success"},
        ]
        engine = ReconciliationEngine()
        engine.import_internal_transactions(internal_records)
        engine.import_channel_transactions(channel_records)
        report = engine.reconcile()
        assert report.matched_count == 1
        assert report.matched_pairs[0].match_type == MatchType.FALLBACK
        assert abs(report.matched_pairs[0].diff_amount) < 0.001

    def test_fallback_amount_rounded_two_decimals_match(self, default_engine, base_time):
        internal_records = [
            {"amount": 99.994, "txn_time": base_time, "status": "success"},
        ]
        channel_records = [
            {"amount": 99.991, "trade_time": base_time, "status": "success"},
        ]
        engine = ReconciliationEngine()
        engine.import_internal_transactions(internal_records)
        engine.import_channel_transactions(channel_records)
        report = engine.reconcile()
        assert report.matched_count == 1


class TestFallbackStatusMismatch:
    def test_fallback_status_mismatch_classified_correctly(self, default_engine, base_time):
        internal_records = [
            {"amount": 150.0, "txn_time": base_time, "status": "success"},
        ]
        channel_records = [
            {"amount": 150.0, "trade_time": base_time, "status": "failed"},
        ]
        default_engine.import_internal_transactions(internal_records)
        default_engine.import_channel_transactions(channel_records)
        report = default_engine.reconcile()
        assert report.matched_count == 0
        assert len(report.internal_discrepancies[DiscrepancyType.STATUS_MISMATCH]) == 1
        assert len(report.channel_discrepancies[DiscrepancyType.STATUS_MISMATCH]) == 1
        assert len(report.internal_discrepancies[DiscrepancyType.CHANNEL_MISSING]) == 0
        assert len(report.channel_discrepancies[DiscrepancyType.INTERNAL_MISSING]) == 0
        disc = report.internal_discrepancies[DiscrepancyType.STATUS_MISMATCH][0]
        assert "Fallback status mismatch" in disc.detail


class TestMatchedAmountBasis:
    def test_matched_amount_uses_channel_amount_after_write_off(self, lenient_engine, base_time):
        lenient_engine.import_internal_transactions([
            make_internal_record("T001", 100.0, base_time),
        ])
        lenient_engine.import_channel_transactions([
            make_channel_record("T001", 99.5, base_time),
        ])
        report = lenient_engine.reconcile()
        assert report.matched_count == 1
        assert report.matched_amount == 99.5
        assert report.tolerance_write_off_diff_amount == 0.5
        assert report.internal_total_amount == 100.0
        assert report.channel_total_amount == 99.5

    def test_exact_match_matched_amount_same_both_sides(self, default_engine, base_time):
        default_engine.import_internal_transactions([
            make_internal_record("T001", 250.0, base_time),
        ])
        default_engine.import_channel_transactions([
            make_channel_record("T001", 250.0, base_time),
        ])
        report = default_engine.reconcile()
        assert report.matched_amount == 250.0
        assert report.internal_total_amount == 250.0
        assert report.channel_total_amount == 250.0
