from __future__ import annotations

import threading
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from .models import (
    Discrepancy,
    DiscrepancyType,
    MatchType,
    MatchedPair,
    ReconciliationError,
    ReconciliationReport,
    ToleranceConfig,
    Transaction,
    TransactionSide,
    TransactionStatus,
)


def normalize_internal_record(record: Dict) -> Transaction:
    txn_id = record.get("txn_id") or record.get("transaction_id") or record.get("order_id")
    amount = float(record.get("amount", 0))
    txn_time = record.get("txn_time") or record.get("pay_time") or record.get("created_at")
    status_str = record.get("status", "success")
    order_id = record.get("order_id")
    if isinstance(txn_time, str):
        txn_time = datetime.fromisoformat(txn_time)
    elif not isinstance(txn_time, datetime):
        txn_time = datetime.now()
    return Transaction(
        txn_id=str(txn_id),
        amount=amount,
        txn_time=txn_time,
        status=TransactionStatus(status_str),
        side=TransactionSide.INTERNAL,
        raw_data=record,
        order_id=str(order_id) if order_id else None,
    )


def normalize_channel_record(record: Dict) -> Transaction:
    txn_id = record.get("txn_id") or record.get("trade_no") or record.get("transaction_id")
    amount = float(record.get("amount", 0))
    txn_time = record.get("txn_time") or record.get("trade_time") or record.get("paid_at")
    status_str = record.get("status", "success")
    order_id = record.get("order_id") or record.get("out_trade_no")
    if isinstance(txn_time, str):
        txn_time = datetime.fromisoformat(txn_time)
    elif not isinstance(txn_time, datetime):
        txn_time = datetime.now()
    return Transaction(
        txn_id=str(txn_id),
        amount=amount,
        txn_time=txn_time,
        status=TransactionStatus(status_str),
        side=TransactionSide.CHANNEL,
        raw_data=record,
        order_id=str(order_id) if order_id else None,
    )


class ReconciliationEngine:
    def __init__(
        self,
        tolerance: Optional[ToleranceConfig] = None,
        fallback_time_window: timedelta = timedelta(minutes=5),
    ) -> None:
        self._tolerance = tolerance or ToleranceConfig()
        self._fallback_time_window = fallback_time_window
        self._internal_txns: Dict[str, Transaction] = {}
        self._channel_txns: Dict[str, Transaction] = {}
        self._reports: Dict[str, ReconciliationReport] = {}
        self._reports_by_time: List[Tuple[datetime, ReconciliationReport]] = []
        self._lock = threading.RLock()

    def import_internal_transactions(self, records: List[Dict]) -> List[Transaction]:
        with self._lock:
            imported = []
            for rec in records:
                txn = normalize_internal_record(rec)
                if txn.txn_id in self._internal_txns:
                    continue
                self._internal_txns[txn.txn_id] = txn
                imported.append(txn)
            return imported

    def import_channel_transactions(self, records: List[Dict]) -> List[Transaction]:
        with self._lock:
            imported = []
            for rec in records:
                txn = normalize_channel_record(rec)
                if txn.txn_id in self._channel_txns:
                    continue
                self._channel_txns[txn.txn_id] = txn
                imported.append(txn)
            return imported

    def get_internal_transaction(self, txn_id: str) -> Optional[Transaction]:
        return self._internal_txns.get(txn_id)

    def get_channel_transaction(self, txn_id: str) -> Optional[Transaction]:
        return self._channel_txns.get(txn_id)

    def list_internal_transactions(self) -> List[Transaction]:
        return list(self._internal_txns.values())

    def list_channel_transactions(self) -> List[Transaction]:
        return list(self._channel_txns.values())

    def clear(self) -> None:
        with self._lock:
            self._internal_txns.clear()
            self._channel_txns.clear()

    @staticmethod
    def _dedup(txns: List[Transaction]) -> Dict[str, Transaction]:
        seen: Dict[str, Transaction] = {}
        for txn in txns:
            if txn.txn_id not in seen:
                seen[txn.txn_id] = txn
        return seen

    def _try_match_by_id(
        self,
        internal_map: Dict[str, Transaction],
        channel_map: Dict[str, Transaction],
        matched_pairs: List[MatchedPair],
        internal_matched: set[str],
        channel_matched: set[str],
        internal_discrepancies: Dict[DiscrepancyType, List[Discrepancy]],
        channel_discrepancies: Dict[DiscrepancyType, List[Discrepancy]],
    ) -> Tuple[int, float]:
        write_off_count = 0
        write_off_diff = 0.0

        for txn_id, itxn in internal_map.items():
            ctxn = channel_map.get(txn_id)
            if ctxn is None:
                continue

            if itxn.status != ctxn.status:
                internal_discrepancies[DiscrepancyType.STATUS_MISMATCH].append(
                    Discrepancy.create(
                        DiscrepancyType.STATUS_MISMATCH,
                        internal_txn=itxn,
                        channel_txn=ctxn,
                        detail=f"Status mismatch: internal={itxn.status.value}, channel={ctxn.status.value}",
                    )
                )
                channel_discrepancies[DiscrepancyType.STATUS_MISMATCH].append(
                    Discrepancy.create(
                        DiscrepancyType.STATUS_MISMATCH,
                        internal_txn=itxn,
                        channel_txn=ctxn,
                        detail=f"Status mismatch: internal={itxn.status.value}, channel={ctxn.status.value}",
                    )
                )
                internal_matched.add(txn_id)
                channel_matched.add(txn_id)
                continue

            if itxn.amount == ctxn.amount:
                matched_pairs.append(MatchedPair(
                    internal_txn=itxn,
                    channel_txn=ctxn,
                    match_type=MatchType.EXACT,
                    diff_amount=0.0,
                ))
                internal_matched.add(txn_id)
                channel_matched.add(txn_id)
            elif self._tolerance.is_within_tolerance(itxn.amount, ctxn.amount):
                diff = self._tolerance.diff_amount(itxn.amount, ctxn.amount)
                matched_pairs.append(MatchedPair(
                    internal_txn=itxn,
                    channel_txn=ctxn,
                    match_type=MatchType.TOLERANCE,
                    diff_amount=diff,
                    write_off=True,
                ))
                write_off_count += 1
                write_off_diff += diff
                internal_matched.add(txn_id)
                channel_matched.add(txn_id)
            else:
                internal_discrepancies[DiscrepancyType.AMOUNT_MISMATCH].append(
                    Discrepancy.create(
                        DiscrepancyType.AMOUNT_MISMATCH,
                        internal_txn=itxn,
                        channel_txn=ctxn,
                        detail=f"Amount mismatch out of tolerance: internal={itxn.amount}, channel={ctxn.amount}",
                    )
                )
                channel_discrepancies[DiscrepancyType.AMOUNT_MISMATCH].append(
                    Discrepancy.create(
                        DiscrepancyType.AMOUNT_MISMATCH,
                        internal_txn=itxn,
                        channel_txn=ctxn,
                        detail=f"Amount mismatch out of tolerance: internal={itxn.amount}, channel={ctxn.amount}",
                    )
                )
                internal_matched.add(txn_id)
                channel_matched.add(txn_id)

        return write_off_count, write_off_diff

    def _try_fallback_match(
        self,
        internal_map: Dict[str, Transaction],
        channel_map: Dict[str, Transaction],
        matched_pairs: List[MatchedPair],
        internal_matched: set[str],
        channel_matched: set[str],
    ) -> Tuple[int, float]:
        write_off_count = 0
        write_off_diff = 0.0

        remaining_internal_ids = [
            tid for tid in internal_map if tid not in internal_matched
        ]

        for ctid, ctxn in channel_map.items():
            if ctid in channel_matched:
                continue

            c_time = ctxn.txn_time.replace(microsecond=0)

            exact_candidates = []
            tolerance_candidates = []

            for itid in remaining_internal_ids:
                itxn = internal_map[itid]
                if itxn.status != ctxn.status:
                    continue
                itime = itxn.txn_time.replace(microsecond=0)
                time_diff = abs((c_time - itime).total_seconds())
                if time_diff > self._fallback_time_window.total_seconds():
                    continue
                if itxn.amount == ctxn.amount:
                    exact_candidates.append((itid, time_diff, 0.0))
                elif self._tolerance.is_within_tolerance(itxn.amount, ctxn.amount):
                    diff = self._tolerance.diff_amount(itxn.amount, ctxn.amount)
                    tolerance_candidates.append((itid, time_diff, diff))

            exact_candidates.sort(key=lambda x: x[1])
            tolerance_candidates.sort(key=lambda x: x[1])

            matched_itid = None
            matched_diff = 0.0
            is_write_off = False

            if exact_candidates:
                matched_itid, _, matched_diff = exact_candidates[0]
                is_write_off = False
            elif tolerance_candidates:
                matched_itid, _, matched_diff = tolerance_candidates[0]
                is_write_off = True

            if matched_itid is not None:
                itxn = internal_map[matched_itid]
                matched_pairs.append(MatchedPair(
                    internal_txn=itxn,
                    channel_txn=ctxn,
                    match_type=MatchType.FALLBACK,
                    diff_amount=matched_diff,
                    write_off=is_write_off,
                ))
                if is_write_off:
                    write_off_count += 1
                    write_off_diff += matched_diff
                internal_matched.add(matched_itid)
                channel_matched.add(ctid)
                remaining_internal_ids.remove(matched_itid)

        return write_off_count, write_off_diff

    def reconcile(
        self,
        time_window: Optional[Tuple[datetime, datetime]] = None,
    ) -> ReconciliationReport:
        with self._lock:
            start_time = datetime.now()

            internal_txns = list(self._internal_txns.values())
            channel_txns = list(self._channel_txns.values())

            if time_window:
                t_start, t_end = time_window
                internal_txns = [t for t in internal_txns if t_start <= t.txn_time <= t_end]
                channel_txns = [t for t in channel_txns if t_start <= t.txn_time <= t_end]

            internal_map = self._dedup(internal_txns)
            channel_map = self._dedup(channel_txns)

            matched_pairs: List[MatchedPair] = []
            internal_matched_ids: set[str] = set()
            channel_matched_ids: set[str] = set()
            total_write_off_count = 0
            total_write_off_diff = 0.0

            internal_discrepancies: Dict[DiscrepancyType, List[Discrepancy]] = {
                DiscrepancyType.CHANNEL_MISSING: [],
                DiscrepancyType.AMOUNT_MISMATCH: [],
                DiscrepancyType.STATUS_MISMATCH: [],
            }
            channel_discrepancies: Dict[DiscrepancyType, List[Discrepancy]] = {
                DiscrepancyType.INTERNAL_MISSING: [],
                DiscrepancyType.AMOUNT_MISMATCH: [],
                DiscrepancyType.STATUS_MISMATCH: [],
            }

            wo_cnt, wo_diff = self._try_match_by_id(
                internal_map,
                channel_map,
                matched_pairs,
                internal_matched_ids,
                channel_matched_ids,
                internal_discrepancies,
                channel_discrepancies,
            )
            total_write_off_count += wo_cnt
            total_write_off_diff += wo_diff

            wo_cnt2, wo_diff2 = self._try_fallback_match(
                internal_map,
                channel_map,
                matched_pairs,
                internal_matched_ids,
                channel_matched_ids,
            )
            total_write_off_count += wo_cnt2
            total_write_off_diff += wo_diff2

            for tid, itxn in internal_map.items():
                if tid not in internal_matched_ids:
                    internal_discrepancies[DiscrepancyType.CHANNEL_MISSING].append(
                        Discrepancy.create(
                            DiscrepancyType.CHANNEL_MISSING,
                            internal_txn=itxn,
                            detail="No matching channel transaction found",
                        )
                    )

            for tid, ctxn in channel_map.items():
                if tid not in channel_matched_ids:
                    channel_discrepancies[DiscrepancyType.INTERNAL_MISSING].append(
                        Discrepancy.create(
                            DiscrepancyType.INTERNAL_MISSING,
                            channel_txn=ctxn,
                            detail="No matching internal transaction found",
                        )
                    )

            internal_total_count = len(internal_map)
            internal_total_amount = sum(t.amount for t in internal_map.values())
            channel_total_count = len(channel_map)
            channel_total_amount = sum(t.amount for t in channel_map.values())
            matched_count = len(matched_pairs)
            matched_amount = sum(p.internal_txn.amount for p in matched_pairs)

            end_time = datetime.now()
            batch_id = str(uuid.uuid4())

            report = ReconciliationReport(
                batch_id=batch_id,
                start_time=start_time,
                end_time=end_time,
                internal_total_count=internal_total_count,
                internal_total_amount=internal_total_amount,
                channel_total_count=channel_total_count,
                channel_total_amount=channel_total_amount,
                matched_count=matched_count,
                matched_amount=matched_amount,
                tolerance_write_off_count=total_write_off_count,
                tolerance_write_off_diff_amount=total_write_off_diff,
                internal_discrepancies=internal_discrepancies,
                channel_discrepancies=channel_discrepancies,
                matched_pairs=matched_pairs,
            )

            self._reports[batch_id] = report
            self._reports_by_time.append((start_time, report))
            return report

    def get_report(self, batch_id: str) -> Optional[ReconciliationReport]:
        return self._reports.get(batch_id)

    def list_reports(self) -> List[ReconciliationReport]:
        return [r for _, r in self._reports_by_time]

    def query_reports(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> List[ReconciliationReport]:
        results = []
        for t, r in self._reports_by_time:
            if start and t < start:
                continue
            if end and t > end:
                continue
            results.append(r)
        return results
