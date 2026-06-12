from __future__ import annotations

from typing import List, Optional

from .exceptions import InvalidIndexError
from .models import AuditLogEntry, VerificationReport, VerificationResult, compute_hash


class AuditLogValidator:
    def verify_chain(
        self,
        entries: List[AuditLogEntry],
        start: int = 0,
        end: Optional[int] = None,
        anchor_hashes: Optional[List[str]] = None,
    ) -> VerificationReport:
        if end is None:
            end = len(entries)

        if start < 0:
            raise InvalidIndexError(f"Start index {start} must be non-negative")
        if end < start:
            raise InvalidIndexError(
                f"End index {end} must be greater than or equal to start index {start}"
            )
        if end > len(entries):
            raise InvalidIndexError(
                f"End index {end} exceeds entries list length {len(entries)}"
            )

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

        for pos in range(total):
            entry = entries[start + pos]
            expected_index = start + pos
            if entry.index != expected_index:
                raise InvalidIndexError(
                    f"Entry at list position {start + pos} has index {entry.index}, "
                    f"but expected index is {expected_index}. "
                    f"Ensure entries list index and start parameter are consistent."
                )

        if anchor_hashes is not None:
            max_entry_index = end - 1
            if max_entry_index >= len(anchor_hashes):
                raise InvalidIndexError(
                    f"anchor_hashes length {len(anchor_hashes)} is insufficient "
                    f"to cover entry index {max_entry_index}. "
                    f"Need at least {max_entry_index + 1} anchor hashes."
                )

        results: List[VerificationResult] = []
        tampered_indices: List[int] = []
        first_tampered: Optional[int] = None
        previous_hash: str = ""
        chain_broken = False

        if start > 0:
            if start - 1 >= len(entries):
                raise InvalidIndexError(
                    f"Cannot access entries[{start - 1}] for anchor hash, entries length is {len(entries)}"
                )
            previous_hash = entries[start - 1].hash

        for pos in range(total):
            i = start + pos
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
            is_propagated = bool(chain_broken)
            anchor_check_done = False
            failure_type = ""
            fail_message = ""
            valid = True
            result_expected_hash = expected_hash

            if not is_propagated:
                if i > start and entry.previous_hash != previous_hash:
                    valid = False
                    failure_type = "previous_hash"
                    fail_message = f"Previous hash mismatch: expected {previous_hash}, got {entry.previous_hash}"
                    if anchor_hashes is not None:
                        fail_message += " (anchor check skipped)"
                elif actual_hash != expected_hash:
                    valid = False
                    failure_type = "content_hash"
                    fail_message = f"Hash mismatch for entry {entry.index}"
                    if anchor_hashes is not None:
                        fail_message += " (anchor check skipped)"
                elif anchor_hashes is not None:
                    anchor_check_done = True
                    if actual_hash != anchor_hashes[entry.index]:
                        valid = False
                        failure_type = "anchor_hash"
                        fail_message = (
                            f"Systemic overwrite detected: entry {entry.index} hash "
                            f"does not match anchor hash from chain state"
                        )
                        result_expected_hash = anchor_hashes[entry.index]
                    else:
                        anchor_check_done = True
            else:
                valid = False
                if i > start and entry.previous_hash != previous_hash:
                    failure_type = "previous_hash"
                    fail_message = (
                        f"[PROPAGATED] Previous hash mismatch: expected {previous_hash}, "
                        f"got {entry.previous_hash}. "
                        f"Chain already broken at index {first_tampered}, entry {entry.index} cannot be trusted."
                    )
                    if anchor_hashes is not None:
                        fail_message += " (anchor check skipped)"
                elif actual_hash != expected_hash:
                    failure_type = "content_hash"
                    fail_message = (
                        f"[PROPAGATED] Hash mismatch for entry {entry.index}. "
                        f"Chain already broken at index {first_tampered}, entry {entry.index} cannot be trusted."
                    )
                    if anchor_hashes is not None:
                        fail_message += " (anchor check skipped)"
                elif anchor_hashes is not None:
                    anchor_check_done = True
                    if actual_hash != anchor_hashes[entry.index]:
                        failure_type = "anchor_hash"
                        fail_message = (
                            f"[PROPAGATED] Systemic overwrite detected: entry {entry.index} hash "
                            f"does not match anchor hash from chain state. "
                            f"Chain already broken at index {first_tampered}, entry {entry.index} cannot be trusted."
                        )
                        result_expected_hash = anchor_hashes[entry.index]
                    else:
                        failure_type = "chain_broken"
                        fail_message = (
                            f"[PROPAGATED] Chain already broken at index {first_tampered}, "
                            f"entry {entry.index} cannot be trusted"
                        )
                else:
                    failure_type = "chain_broken"
                    fail_message = (
                        f"[PROPAGATED] Chain already broken at index {first_tampered}, "
                        f"entry {entry.index} cannot be trusted"
                    )

            if not valid:
                results.append(
                    VerificationResult(
                        index=entry.index,
                        valid=False,
                        expected_hash=result_expected_hash,
                        actual_hash=actual_hash,
                        message=fail_message,
                        is_propagated_failure=is_propagated,
                        anchor_check_performed=anchor_check_done,
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
                        is_propagated_failure=False,
                        anchor_check_performed=anchor_check_done,
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
        anchor_hash: Optional[str] = None,
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
        anchor_check_done = False

        if entry.previous_hash != previous_hash:
            message = f"Previous hash mismatch: expected {previous_hash}, got {entry.previous_hash}"
            if anchor_hash is not None:
                message += " (anchor check skipped)"
            return VerificationResult(
                index=entry.index,
                valid=False,
                expected_hash=expected_hash,
                actual_hash=actual_hash,
                message=message,
                is_propagated_failure=False,
                anchor_check_performed=anchor_check_done,
            )

        if actual_hash != expected_hash:
            message = f"Hash mismatch for entry {entry.index}"
            if anchor_hash is not None:
                message += " (anchor check skipped)"
            return VerificationResult(
                index=entry.index,
                valid=False,
                expected_hash=expected_hash,
                actual_hash=actual_hash,
                message=message,
                is_propagated_failure=False,
                anchor_check_performed=anchor_check_done,
            )

        if anchor_hash is not None:
            anchor_check_done = True
            if actual_hash != anchor_hash:
                return VerificationResult(
                    index=entry.index,
                    valid=False,
                    expected_hash=anchor_hash,
                    actual_hash=actual_hash,
                    message=f"Systemic overwrite detected: entry {entry.index} hash does not match anchor hash from chain state",
                    is_propagated_failure=False,
                    anchor_check_performed=anchor_check_done,
                )

        return VerificationResult(
            index=entry.index,
            valid=True,
            expected_hash=expected_hash,
            actual_hash=actual_hash,
            message=f"Entry {entry.index} verified successfully",
            is_propagated_failure=False,
            anchor_check_performed=anchor_check_done,
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
