from __future__ import annotations

from typing import List, Optional

from .models import AuditLogEntry, VerificationReport, VerificationResult, compute_hash


class AuditLogValidator:
    def verify_chain(
        self,
        entries: List[AuditLogEntry],
        start: int = 0,
        end: Optional[int] = None,
    ) -> VerificationReport:
        if end is None:
            end = len(entries)

        total = end - start
        if total <= 0:
            return VerificationReport(
                is_valid=True,
                total_entries=0,
                passed_ranges=[],
                failed_ranges=[],
                tampered_indices=[],
                results=[],
                first_tampered_index=None,
            )

        results: List[VerificationResult] = []
        tampered_indices: List[int] = []
        first_tampered: Optional[int] = None
        previous_hash: str = ""

        if start > 0 and start < len(entries):
            previous_hash = entries[start - 1].hash

        chain_broken = False
        for i in range(start, end):
            entry = entries[i]
            expected_content = AuditLogEntry(
                index=entry.index,
                event_type=entry.event_type,
                subject=entry.subject,
                target=entry.target,
                timestamp=entry.timestamp,
                details=entry.details,
                previous_hash=previous_hash,
            )
            expected_hash = expected_content.compute_hash()

            actual_hash = entry.hash
            valid = True
            fail_message = ""

            if i > start and entry.previous_hash != previous_hash:
                valid = False
                fail_message = f"Previous hash mismatch: expected {previous_hash}, got {entry.previous_hash}"
            elif actual_hash != expected_hash:
                valid = False
                fail_message = f"Hash mismatch for entry {entry.index}"
            elif chain_broken:
                valid = False
                fail_message = f"Chain already broken at index {first_tampered}, entry {entry.index} cannot be trusted"

            if not valid:
                results.append(
                    VerificationResult(
                        index=entry.index,
                        valid=False,
                        expected_hash=expected_hash,
                        actual_hash=actual_hash,
                        message=fail_message,
                    )
                )
                if first_tampered is None and not chain_broken:
                    first_tampered = entry.index
                    chain_broken = True
                tampered_indices.append(entry.index)
            else:
                results.append(
                    VerificationResult(
                        index=entry.index,
                        valid=True,
                        expected_hash=expected_hash,
                        actual_hash=actual_hash,
                        message=f"Entry {entry.index} verified successfully",
                    )
                )

            previous_hash = entry.hash

        passed_ranges = self._compute_ranges(results, True)
        failed_ranges = self._compute_ranges(results, False)

        is_valid = len(tampered_indices) == 0

        return VerificationReport(
            is_valid=is_valid,
            total_entries=total,
            passed_ranges=passed_ranges,
            failed_ranges=failed_ranges,
            tampered_indices=tampered_indices,
            results=results,
            first_tampered_index=first_tampered,
        )

    def verify_entry(
        self,
        entry: AuditLogEntry,
        previous_hash: str = "",
    ) -> VerificationResult:
        expected_content = AuditLogEntry(
            index=entry.index,
            event_type=entry.event_type,
            subject=entry.subject,
            target=entry.target,
            timestamp=entry.timestamp,
            details=entry.details,
            previous_hash=previous_hash,
        )
        expected_hash = expected_content.compute_hash()
        actual_hash = entry.hash

        if entry.previous_hash != previous_hash:
            return VerificationResult(
                index=entry.index,
                valid=False,
                expected_hash=expected_hash,
                actual_hash=actual_hash,
                message=f"Previous hash mismatch: expected {previous_hash}, got {entry.previous_hash}",
            )

        if actual_hash != expected_hash:
            return VerificationResult(
                index=entry.index,
                valid=False,
                expected_hash=expected_hash,
                actual_hash=actual_hash,
                message=f"Hash mismatch for entry {entry.index}",
            )

        return VerificationResult(
            index=entry.index,
            valid=True,
            expected_hash=expected_hash,
            actual_hash=actual_hash,
            message=f"Entry {entry.index} verified successfully",
        )

    def _compute_ranges(
        self, results: List[VerificationResult], valid: bool
    ) -> List[tuple]:
        ranges: List[tuple] = []
        if not results:
            return ranges

        start_idx: Optional[int] = None
        prev_idx: Optional[int] = None

        for r in results:
            if r.valid == valid:
                if start_idx is None:
                    start_idx = r.index
                prev_idx = r.index
            else:
                if start_idx is not None and prev_idx is not None:
                    ranges.append((start_idx, prev_idx))
                    start_idx = None
                    prev_idx = None

        if start_idx is not None and prev_idx is not None:
            ranges.append((start_idx, prev_idx))

        return ranges


__all__ = ["AuditLogValidator"]
