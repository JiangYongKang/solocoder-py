from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Dict, List, Optional

from .exceptions import (
    DuplicateAssignmentError,
    EmptyStaffListError,
    InvalidDateRangeError,
    OverlappingAssignmentError,
    PastDateSwapError,
    ShiftNotFoundError,
    ShiftSchedulerError,
    StaffNotFoundError,
    SwapRequestAlreadyProcessedError,
    SwapRequestNotFoundError,
    SwapRequestNotAuthorizedError,
    UncoveredGapError,
)
from .models import (
    GapReport,
    GapType,
    ShiftAssignment,
    Staff,
    StaffId,
    SwapRequest,
    SwapRequestStatus,
    ValidationResult,
)


@dataclass
class ShiftScheduler:
    _staff: Dict[StaffId, Staff] = field(default_factory=dict, init=False)
    _schedule: Dict[date, List[ShiftAssignment]] = field(default_factory=dict, init=False)
    _swap_requests: Dict[str, SwapRequest] = field(default_factory=dict, init=False)
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False)

    def register_staff(self, staff: Staff) -> StaffId:
        if staff is None:
            raise ValueError("staff cannot be None")
        with self._lock:
            if staff.staff_id in self._staff:
                raise ShiftSchedulerError(f"Staff {staff.staff_id} already registered")
            self._staff[staff.staff_id] = staff
            return staff.staff_id

    def get_staff(self, staff_id: StaffId) -> Optional[Staff]:
        with self._lock:
            return self._staff.get(staff_id)

    def get_all_staff(self) -> List[Staff]:
        with self._lock:
            return list(self._staff.values())

    def remove_staff(self, staff_id: StaffId) -> bool:
        with self._lock:
            if staff_id not in self._staff:
                return False
            del self._staff[staff_id]
            return True

    def generate_rotation_schedule(
        self,
        staff_order: List[StaffId],
        start_date: date,
        end_date: date,
    ) -> Dict[date, List[StaffId]]:
        if start_date is None or end_date is None:
            raise ValueError("start_date and end_date cannot be None")
        if start_date > end_date:
            raise InvalidDateRangeError("start_date must be before or equal to end_date")
        if not staff_order:
            raise EmptyStaffListError("staff_order cannot be empty")

        with self._lock:
            for sid in staff_order:
                if sid not in self._staff:
                    raise StaffNotFoundError(f"Staff {sid} not found")

            result: Dict[date, List[StaffId]] = {}
            staff_count = len(staff_order)
            current_date = start_date
            day_index = 0

            while current_date <= end_date:
                staff_idx = day_index % staff_count
                assigned_staff = staff_order[staff_idx]

                if current_date in self._schedule:
                    already_assigned = any(
                        ex.staff_id == assigned_staff
                        for ex in self._schedule[current_date]
                    )
                    if not already_assigned:
                        self._schedule[current_date].append(
                            ShiftAssignment(shift_date=current_date, staff_id=assigned_staff)
                        )
                else:
                    self._schedule[current_date] = [
                        ShiftAssignment(shift_date=current_date, staff_id=assigned_staff)
                    ]

                result[current_date] = [a.staff_id for a in self._schedule[current_date]]

                current_date += timedelta(days=1)
                day_index += 1

            return result

    def set_shift(self, shift_date: date, staff_id: StaffId) -> None:
        if shift_date is None:
            raise ValueError("shift_date cannot be None")
        if staff_id is None:
            raise ValueError("staff_id cannot be None")
        with self._lock:
            if staff_id not in self._staff:
                raise StaffNotFoundError(f"Staff {staff_id} not found")
            assignment = ShiftAssignment(shift_date=shift_date, staff_id=staff_id)
            if shift_date in self._schedule:
                self._schedule[shift_date].append(assignment)
            else:
                self._schedule[shift_date] = [assignment]

    def clear_shift(self, shift_date: date, staff_id: Optional[StaffId] = None) -> bool:
        if shift_date is None:
            raise ValueError("shift_date cannot be None")
        with self._lock:
            if shift_date not in self._schedule:
                return False
            if staff_id is None:
                del self._schedule[shift_date]
                return True
            assignments = self._schedule[shift_date]
            original_len = len(assignments)
            self._schedule[shift_date] = [a for a in assignments if a.staff_id != staff_id]
            if not self._schedule[shift_date]:
                del self._schedule[shift_date]
            return len(self._schedule.get(shift_date, [])) < original_len

    def get_assignment(self, shift_date: date) -> List[StaffId]:
        with self._lock:
            if shift_date not in self._schedule:
                return []
            return [a.staff_id for a in self._schedule[shift_date]]

    def get_schedule_range(self, start_date: date, end_date: date) -> Dict[date, List[StaffId]]:
        if start_date is None or end_date is None:
            raise ValueError("start_date and end_date cannot be None")
        if start_date > end_date:
            raise InvalidDateRangeError("start_date must be before or equal to end_date")
        with self._lock:
            result: Dict[date, List[StaffId]] = {}
            current = start_date
            while current <= end_date:
                result[current] = list(self.get_assignment(current))
                current += timedelta(days=1)
            return result

    def create_swap_request(
        self,
        requester_id: StaffId,
        responder_id: StaffId,
        requester_date: date,
        responder_date: date,
        today: Optional[date] = None,
    ) -> str:
        if requester_id is None:
            raise ValueError("requester_id cannot be None")
        if responder_id is None:
            raise ValueError("responder_id cannot be None")
        if requester_date is None:
            raise ValueError("requester_date cannot be None")
        if responder_date is None:
            raise ValueError("responder_date cannot be None")

        check_date = today if today is not None else date.today()

        if requester_date < check_date:
            raise PastDateSwapError("Cannot swap a past date for requester")
        if responder_date < check_date:
            raise PastDateSwapError("Cannot swap a past date for responder")

        with self._lock:
            if requester_id not in self._staff:
                raise StaffNotFoundError(f"Requester {requester_id} not found")
            if responder_id not in self._staff:
                raise StaffNotFoundError(f"Responder {responder_id} not found")

            requester_assignments = self._schedule.get(requester_date, [])
            requester_assigned = any(a.staff_id == requester_id for a in requester_assignments)
            if not requester_assigned:
                raise ShiftNotFoundError(
                    f"Requester {requester_id} is not assigned to {requester_date}"
                )

            responder_assignments = self._schedule.get(responder_date, [])
            responder_assigned = any(a.staff_id == responder_id for a in responder_assignments)
            if not responder_assigned:
                raise ShiftNotFoundError(
                    f"Responder {responder_id} is not assigned to {responder_date}"
                )

            request_id = f"swap-{uuid.uuid4().hex[:12]}"
            swap = SwapRequest(
                request_id=request_id,
                requester_id=requester_id,
                responder_id=responder_id,
                requester_date=requester_date,
                responder_date=responder_date,
            )
            self._swap_requests[request_id] = swap
            return request_id

    def get_swap_request(self, request_id: str) -> Optional[SwapRequest]:
        with self._lock:
            return self._swap_requests.get(request_id)

    def get_all_swap_requests(self) -> List[SwapRequest]:
        with self._lock:
            return list(self._swap_requests.values())

    def approve_swap_request(
        self,
        request_id: str,
        approver_id: StaffId,
    ) -> None:
        if not request_id or not request_id.strip():
            raise ValueError("request_id cannot be empty")
        if approver_id is None:
            raise ValueError("approver_id cannot be None")

        with self._lock:
            swap = self._swap_requests.get(request_id)
            if swap is None:
                raise SwapRequestNotFoundError(f"Swap request {request_id} not found")

            if approver_id != swap.responder_id:
                raise SwapRequestNotAuthorizedError(
                    f"Only responder {swap.responder_id} can approve this swap"
                )

            if swap.status != SwapRequestStatus.PENDING:
                raise SwapRequestAlreadyProcessedError(
                    f"Swap request is already {swap.status.value}"
                )

            swap.approve()
            self._execute_swap(swap)

    def reject_swap_request(
        self,
        request_id: str,
        rejecter_id: StaffId,
    ) -> None:
        if not request_id or not request_id.strip():
            raise ValueError("request_id cannot be empty")
        if rejecter_id is None:
            raise ValueError("rejecter_id cannot be None")

        with self._lock:
            swap = self._swap_requests.get(request_id)
            if swap is None:
                raise SwapRequestNotFoundError(f"Swap request {request_id} not found")

            if rejecter_id != swap.responder_id:
                raise SwapRequestNotAuthorizedError(
                    f"Only responder {swap.responder_id} can reject this swap"
                )

            if swap.status != SwapRequestStatus.PENDING:
                raise SwapRequestAlreadyProcessedError(
                    f"Swap request is already {swap.status.value}"
                )

            swap.reject()

    def _execute_swap(self, swap: SwapRequest) -> None:
        requester_date = swap.requester_date
        responder_date = swap.responder_date
        requester_id = swap.requester_id
        responder_id = swap.responder_id

        req_assignments = self._schedule.get(requester_date, [])
        req_kept = [a for a in req_assignments if a.staff_id != requester_id]
        req_kept.append(ShiftAssignment(shift_date=requester_date, staff_id=responder_id))
        self._schedule[requester_date] = req_kept

        resp_assignments = self._schedule.get(responder_date, [])
        resp_kept = [a for a in resp_assignments if a.staff_id != responder_id]
        resp_kept.append(ShiftAssignment(shift_date=responder_date, staff_id=requester_id))
        self._schedule[responder_date] = resp_kept

        swap.mark_effective()

    def validate_schedule(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> ValidationResult:
        with self._lock:
            if not self._schedule:
                return ValidationResult(is_valid=True, gaps=[])

            if start_date is None:
                start_date = min(self._schedule.keys())
            if end_date is None:
                end_date = max(self._schedule.keys())

            if start_date > end_date:
                raise InvalidDateRangeError("start_date must be before or equal to end_date")

            gaps: List[GapReport] = []
            current = start_date

            while current <= end_date:
                assignments = self._schedule.get(current, [])
                staff_list = [a.staff_id for a in assignments]

                if len(assignments) == 0:
                    gaps.append(
                        GapReport(
                            gap_type=GapType.UNCOVERED,
                            shift_date=current,
                            staff_ids=[],
                            message=f"No staff assigned to {current}",
                        )
                    )
                elif len(assignments) > 1:
                    gaps.append(
                        GapReport(
                            gap_type=GapType.DUPLICATE,
                            shift_date=current,
                            staff_ids=staff_list,
                            message=f"Multiple staff ({len(assignments)}) assigned to {current}",
                        )
                    )

                current += timedelta(days=1)

            is_valid = len(gaps) == 0
            return ValidationResult(is_valid=is_valid, gaps=gaps)

    def validate_or_raise(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> None:
        result = self.validate_schedule(start_date, end_date)
        if result.is_valid:
            return

        uncovered_dates = [g.shift_date for g in result.gaps if g.is_uncovered]
        duplicate_dates = [g.shift_date for g in result.gaps if g.is_duplicate]

        messages: List[str] = []
        if uncovered_dates:
            messages.append(f"Uncovered gaps on: {uncovered_dates}")
        if duplicate_dates:
            messages.append(f"Duplicate assignments on: {duplicate_dates}")

        if uncovered_dates and duplicate_dates:
            raise OverlappingAssignmentError("; ".join(messages))
        elif uncovered_dates:
            raise UncoveredGapError("; ".join(messages))
        elif duplicate_dates:
            raise DuplicateAssignmentError("; ".join(messages))

    def clear_schedule(self) -> None:
        with self._lock:
            self._schedule.clear()

    def clear_swap_requests(self) -> None:
        with self._lock:
            self._swap_requests.clear()
