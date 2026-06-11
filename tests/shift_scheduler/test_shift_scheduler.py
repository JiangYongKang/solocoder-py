from __future__ import annotations

from datetime import date, timedelta

import pytest

from solocoder_py.shift_scheduler import (
    DuplicateAssignmentError,
    EmptyStaffListError,
    GapReport,
    GapType,
    InvalidDateRangeError,
    OverlappingAssignmentError,
    PastDateSwapError,
    ShiftAssignment,
    ShiftNotFoundError,
    ShiftScheduler,
    Staff,
    StaffId,
    StaffNotFoundError,
    SwapRequest,
    SwapRequestAlreadyProcessedError,
    SwapRequestNotFoundError,
    SwapRequestNotAuthorizedError,
    SwapRequestStatus,
    UncoveredGapError,
    ValidationResult,
)

from .conftest import (
    date_n_days_from_today,
    make_scheduler_with_staff,
    make_staff_list,
    register_staff,
)


class TestStaffIdModel:
    def test_staff_id_creation(self):
        sid = StaffId("staff-1")
        assert sid.value == "staff-1"

    def test_staff_id_str(self):
        sid = StaffId("engineer-alice")
        assert str(sid) == "engineer-alice"

    def test_staff_id_empty_rejected(self):
        with pytest.raises(ValueError, match="StaffId cannot be empty"):
            StaffId("")

    def test_staff_id_whitespace_rejected(self):
        with pytest.raises(ValueError, match="StaffId cannot be empty"):
            StaffId("   ")

    def test_staff_id_equality(self):
        a = StaffId("staff-1")
        b = StaffId("staff-1")
        c = StaffId("staff-2")
        assert a == b
        assert a != c


class TestStaffModel:
    def test_staff_creation(self):
        staff = Staff(staff_id=StaffId("staff-1"), name="Alice")
        assert staff.staff_id.value == "staff-1"
        assert staff.name == "Alice"

    def test_staff_staff_id_none_rejected(self):
        with pytest.raises(ValueError, match="staff_id cannot be None"):
            Staff(staff_id=None, name="Alice")

    def test_staff_name_empty_rejected(self):
        with pytest.raises(ValueError, match="name cannot be empty"):
            Staff(staff_id=StaffId("staff-1"), name="")

    def test_staff_name_whitespace_rejected(self):
        with pytest.raises(ValueError, match="name cannot be empty"):
            Staff(staff_id=StaffId("staff-1"), name="   ")


class TestShiftAssignmentModel:
    def test_assignment_creation(self):
        d = date(2026, 1, 1)
        sid = StaffId("staff-1")
        assignment = ShiftAssignment(shift_date=d, staff_id=sid)
        assert assignment.shift_date == d
        assert assignment.staff_id == sid

    def test_assignment_date_none_rejected(self):
        with pytest.raises(ValueError, match="shift_date cannot be None"):
            ShiftAssignment(shift_date=None, staff_id=StaffId("staff-1"))

    def test_assignment_staff_none_rejected(self):
        with pytest.raises(ValueError, match="staff_id cannot be None"):
            ShiftAssignment(shift_date=date(2026, 1, 1), staff_id=None)


class TestSwapRequestModel:
    def test_swap_request_creation(self):
        requester = StaffId("staff-1")
        responder = StaffId("staff-2")
        req_date = date(2026, 6, 15)
        resp_date = date(2026, 6, 16)

        swap = SwapRequest(
            request_id="swap-1",
            requester_id=requester,
            responder_id=responder,
            requester_date=req_date,
            responder_date=resp_date,
        )

        assert swap.request_id == "swap-1"
        assert swap.requester_id == requester
        assert swap.responder_id == responder
        assert swap.requester_date == req_date
        assert swap.responder_date == resp_date
        assert swap.status == SwapRequestStatus.PENDING
        assert swap.is_pending is True
        assert swap.is_approved is False
        assert swap.is_rejected is False
        assert swap.is_effective is False

    def test_swap_request_empty_id_rejected(self):
        with pytest.raises(ValueError, match="request_id cannot be empty"):
            SwapRequest(
                request_id="",
                requester_id=StaffId("s1"),
                responder_id=StaffId("s2"),
                requester_date=date(2026, 1, 1),
                responder_date=date(2026, 1, 2),
            )

    def test_swap_request_self_swap_rejected(self):
        with pytest.raises(ValueError, match="Cannot swap shifts with yourself"):
            SwapRequest(
                request_id="swap-1",
                requester_id=StaffId("s1"),
                responder_id=StaffId("s1"),
                requester_date=date(2026, 1, 1),
                responder_date=date(2026, 1, 2),
            )

    def test_swap_request_approve(self):
        swap = SwapRequest(
            request_id="swap-1",
            requester_id=StaffId("s1"),
            responder_id=StaffId("s2"),
            requester_date=date(2026, 1, 1),
            responder_date=date(2026, 1, 2),
        )
        swap.approve()
        assert swap.status == SwapRequestStatus.APPROVED
        assert swap.is_approved is True
        assert swap.processed_at is not None

    def test_swap_request_approve_when_not_pending(self):
        swap = SwapRequest(
            request_id="swap-1",
            requester_id=StaffId("s1"),
            responder_id=StaffId("s2"),
            requester_date=date(2026, 1, 1),
            responder_date=date(2026, 1, 2),
        )
        swap.reject()
        with pytest.raises(ValueError, match="Swap request is not pending"):
            swap.approve()

    def test_swap_request_reject(self):
        swap = SwapRequest(
            request_id="swap-1",
            requester_id=StaffId("s1"),
            responder_id=StaffId("s2"),
            requester_date=date(2026, 1, 1),
            responder_date=date(2026, 1, 2),
        )
        swap.reject()
        assert swap.status == SwapRequestStatus.REJECTED
        assert swap.is_rejected is True

    def test_swap_request_mark_effective(self):
        swap = SwapRequest(
            request_id="swap-1",
            requester_id=StaffId("s1"),
            responder_id=StaffId("s2"),
            requester_date=date(2026, 1, 1),
            responder_date=date(2026, 1, 2),
        )
        swap.approve()
        swap.mark_effective()
        assert swap.status == SwapRequestStatus.EFFECTIVE
        assert swap.is_effective is True

    def test_swap_request_mark_effective_without_approval(self):
        swap = SwapRequest(
            request_id="swap-1",
            requester_id=StaffId("s1"),
            responder_id=StaffId("s2"),
            requester_date=date(2026, 1, 1),
            responder_date=date(2026, 1, 2),
        )
        with pytest.raises(ValueError, match="Swap request must be approved"):
            swap.mark_effective()


class TestGapReportModel:
    def test_uncovered_gap(self):
        d = date(2026, 1, 1)
        gap = GapReport(
            gap_type=GapType.UNCOVERED,
            shift_date=d,
            staff_ids=[],
            message="No staff assigned",
        )
        assert gap.is_uncovered is True
        assert gap.is_duplicate is False
        assert gap.shift_date == d

    def test_duplicate_gap(self):
        d = date(2026, 1, 1)
        gap = GapReport(
            gap_type=GapType.DUPLICATE,
            shift_date=d,
            staff_ids=[StaffId("s1"), StaffId("s2")],
            message="Multiple staff",
        )
        assert gap.is_uncovered is False
        assert gap.is_duplicate is True

    def test_gap_report_date_none_rejected(self):
        with pytest.raises(ValueError, match="shift_date cannot be None"):
            GapReport(gap_type=GapType.UNCOVERED, shift_date=None)


class TestValidationResultModel:
    def test_valid_result(self):
        result = ValidationResult(is_valid=True, gaps=[])
        assert result.is_valid is True
        assert result.uncovered_count == 0
        assert result.duplicate_count == 0

    def test_invalid_result_with_gaps(self):
        d1 = date(2026, 1, 1)
        d2 = date(2026, 1, 2)
        gaps = [
            GapReport(gap_type=GapType.UNCOVERED, shift_date=d1),
            GapReport(gap_type=GapType.DUPLICATE, shift_date=d2),
            GapReport(gap_type=GapType.DUPLICATE, shift_date=d2),
        ]
        result = ValidationResult(is_valid=False, gaps=gaps)
        assert result.is_valid is False
        assert result.uncovered_count == 1
        assert result.duplicate_count == 2


class TestNormalFlowRotationGeneration:
    def test_multiple_staff_weekly_rotation(self):
        scheduler, staff_ids = make_scheduler_with_staff(5)
        start = date(2026, 6, 15)
        end = date(2026, 6, 21)

        schedule = scheduler.generate_rotation_schedule(staff_ids, start, end)

        assert len(schedule) == 7
        assert schedule[date(2026, 6, 15)] == staff_ids[0]
        assert schedule[date(2026, 6, 16)] == staff_ids[1]
        assert schedule[date(2026, 6, 17)] == staff_ids[2]
        assert schedule[date(2026, 6, 18)] == staff_ids[3]
        assert schedule[date(2026, 6, 19)] == staff_ids[4]
        assert schedule[date(2026, 6, 20)] == staff_ids[0]
        assert schedule[date(2026, 6, 21)] == staff_ids[1]

        result = scheduler.validate_schedule(start, end)
        assert result.is_valid is True
        assert len(result.gaps) == 0

    def test_validate_passes_no_anomalies(self):
        scheduler, staff_ids = make_scheduler_with_staff(3)
        start = date(2026, 7, 1)
        end = date(2026, 7, 30)

        scheduler.generate_rotation_schedule(staff_ids, start, end)
        result = scheduler.validate_schedule(start, end)

        assert result.is_valid is True
        assert result.uncovered_count == 0
        assert result.duplicate_count == 0


class TestNormalFlowSwapAdjustment:
    def test_two_person_swap_successfully_updates_schedule(self):
        scheduler, staff_ids = make_scheduler_with_staff(3)
        s1, s2, s3 = staff_ids
        today = date(2026, 6, 10)
        start = date(2026, 6, 15)
        end = date(2026, 6, 21)

        scheduler.generate_rotation_schedule(staff_ids, start, end)

        assert scheduler.get_assignment(date(2026, 6, 15)) == [s1]
        assert scheduler.get_assignment(date(2026, 6, 16)) == [s2]

        request_id = scheduler.create_swap_request(
            requester_id=s1,
            responder_id=s2,
            requester_date=date(2026, 6, 15),
            responder_date=date(2026, 6, 16),
            today=today,
        )

        swap = scheduler.get_swap_request(request_id)
        assert swap is not None
        assert swap.is_pending is True

        scheduler.approve_swap_request(request_id, approver_id=s2)

        swap = scheduler.get_swap_request(request_id)
        assert swap.is_effective is True

        assert scheduler.get_assignment(date(2026, 6, 15)) == [s2]
        assert scheduler.get_assignment(date(2026, 6, 16)) == [s1]

        result = scheduler.validate_schedule(start, end)
        assert result.is_valid is True


class TestBoundarySinglePersonRotation:
    def test_single_staff_everyday_same_person(self):
        scheduler, staff_ids = make_scheduler_with_staff(1)
        only_staff = staff_ids[0]
        start = date(2026, 5, 1)
        end = date(2026, 5, 31)

        schedule = scheduler.generate_rotation_schedule(staff_ids, start, end)

        assert len(schedule) == 31
        for d, assigned in schedule.items():
            assert assigned == only_staff
        for i in range(31):
            current = start + timedelta(days=i)
            assert scheduler.get_assignment(current) == [only_staff]

        result = scheduler.validate_schedule(start, end)
        assert result.is_valid is True


class TestBoundaryTwoPersonAlternation:
    def test_two_staff_alternate_daily(self):
        scheduler, staff_ids = make_scheduler_with_staff(2)
        s1, s2 = staff_ids
        start = date(2026, 4, 1)
        end = date(2026, 4, 10)

        schedule = scheduler.generate_rotation_schedule(staff_ids, start, end)

        assert schedule[date(2026, 4, 1)] == s1
        assert schedule[date(2026, 4, 2)] == s2
        assert schedule[date(2026, 4, 3)] == s1
        assert schedule[date(2026, 4, 4)] == s2
        assert schedule[date(2026, 4, 5)] == s1
        assert schedule[date(2026, 4, 6)] == s2
        assert schedule[date(2026, 4, 7)] == s1
        assert schedule[date(2026, 4, 8)] == s2
        assert schedule[date(2026, 4, 9)] == s1
        assert schedule[date(2026, 4, 10)] == s2

        result = scheduler.validate_schedule(start, end)
        assert result.is_valid is True


class TestBoundaryCrossCycleRotation:
    def test_cross_cycle_seamless_wraparound(self):
        scheduler, staff_ids = make_scheduler_with_staff(3)
        s1, s2, s3 = staff_ids

        start = date(2026, 6, 28)
        end = date(2026, 7, 4)

        schedule = scheduler.generate_rotation_schedule(staff_ids, start, end)

        expected = [
            (date(2026, 6, 28), s1),
            (date(2026, 6, 29), s2),
            (date(2026, 6, 30), s3),
            (date(2026, 7, 1), s1),
            (date(2026, 7, 2), s2),
            (date(2026, 7, 3), s3),
            (date(2026, 7, 4), s1),
        ]
        for d, expected_staff in expected:
            assert schedule[d] == expected_staff
            assert scheduler.get_assignment(d) == [expected_staff]

        end_of_june = date(2026, 6, 30)
        start_of_july = date(2026, 7, 1)
        assert scheduler.get_assignment(end_of_june) == [s3]
        assert scheduler.get_assignment(start_of_july) == [s1]

        result = scheduler.validate_schedule(start, end)
        assert result.is_valid is True

    def test_cross_year_boundary(self):
        scheduler, staff_ids = make_scheduler_with_staff(4)
        s1, s2, s3, s4 = staff_ids

        start = date(2026, 12, 29)
        end = date(2027, 1, 3)

        schedule = scheduler.generate_rotation_schedule(staff_ids, start, end)

        assert schedule[date(2026, 12, 29)] == s1
        assert schedule[date(2026, 12, 30)] == s2
        assert schedule[date(2026, 12, 31)] == s3
        assert schedule[date(2027, 1, 1)] == s4
        assert schedule[date(2027, 1, 2)] == s1
        assert schedule[date(2027, 1, 3)] == s2

        result = scheduler.validate_schedule(start, end)
        assert result.is_valid is True


class TestExceptionSwapRejected:
    def test_swap_not_effective_when_rejected(self):
        scheduler, staff_ids = make_scheduler_with_staff(3)
        s1, s2, s3 = staff_ids
        today = date(2026, 6, 10)
        start = date(2026, 6, 15)
        end = date(2026, 6, 21)

        scheduler.generate_rotation_schedule(staff_ids, start, end)

        original_s1_date = scheduler.get_assignment(date(2026, 6, 15))
        original_s2_date = scheduler.get_assignment(date(2026, 6, 16))

        request_id = scheduler.create_swap_request(
            requester_id=s1,
            responder_id=s2,
            requester_date=date(2026, 6, 15),
            responder_date=date(2026, 6, 16),
            today=today,
        )

        scheduler.reject_swap_request(request_id, rejecter_id=s2)

        swap = scheduler.get_swap_request(request_id)
        assert swap.is_rejected is True
        assert swap.is_effective is False

        assert scheduler.get_assignment(date(2026, 6, 15)) == original_s1_date
        assert scheduler.get_assignment(date(2026, 6, 16)) == original_s2_date

    def test_reject_not_authorized_wrong_person(self):
        scheduler, staff_ids = make_scheduler_with_staff(3)
        s1, s2, s3 = staff_ids
        today = date(2026, 6, 10)
        start = date(2026, 6, 15)
        end = date(2026, 6, 21)

        scheduler.generate_rotation_schedule(staff_ids, start, end)

        request_id = scheduler.create_swap_request(
            requester_id=s1,
            responder_id=s2,
            requester_date=date(2026, 6, 15),
            responder_date=date(2026, 6, 16),
            today=today,
        )

        with pytest.raises(SwapRequestNotAuthorizedError):
            scheduler.reject_swap_request(request_id, rejecter_id=s3)

        swap = scheduler.get_swap_request(request_id)
        assert swap.is_pending is True


class TestExceptionPastDateSwap:
    def test_reject_swap_requester_past_date(self):
        scheduler, staff_ids = make_scheduler_with_staff(3)
        s1, s2, s3 = staff_ids
        today = date(2026, 6, 15)
        start = date(2026, 6, 10)
        end = date(2026, 6, 20)

        scheduler.generate_rotation_schedule(staff_ids, start, end)

        with pytest.raises(PastDateSwapError, match="past date for requester"):
            scheduler.create_swap_request(
                requester_id=s1,
                responder_id=s2,
                requester_date=date(2026, 6, 12),
                responder_date=date(2026, 6, 18),
                today=today,
            )

    def test_reject_swap_responder_past_date(self):
        scheduler, staff_ids = make_scheduler_with_staff(3)
        s1, s2, s3 = staff_ids
        today = date(2026, 6, 15)
        start = date(2026, 6, 10)
        end = date(2026, 6, 20)

        scheduler.generate_rotation_schedule(staff_ids, start, end)

        with pytest.raises(PastDateSwapError, match="past date for responder"):
            scheduler.create_swap_request(
                requester_id=s1,
                responder_id=s2,
                requester_date=date(2026, 6, 18),
                responder_date=date(2026, 6, 12),
                today=today,
            )

    def test_swap_on_today_is_allowed(self):
        scheduler, staff_ids = make_scheduler_with_staff(3)
        s1, s2, s3 = staff_ids
        today = date(2026, 6, 15)
        start = date(2026, 6, 15)
        end = date(2026, 6, 21)

        scheduler.generate_rotation_schedule(staff_ids, start, end)

        request_id = scheduler.create_swap_request(
            requester_id=s1,
            responder_id=s2,
            requester_date=date(2026, 6, 15),
            responder_date=date(2026, 6, 16),
            today=today,
        )

        assert request_id is not None
        swap = scheduler.get_swap_request(request_id)
        assert swap.is_pending is True


class TestExceptionGapUncovered:
    def test_detect_uncovered_day(self):
        scheduler, staff_ids = make_scheduler_with_staff(2)
        s1, s2 = staff_ids
        start = date(2026, 8, 1)
        end = date(2026, 8, 5)

        scheduler.generate_rotation_schedule(staff_ids, start, end)

        scheduler.clear_shift(date(2026, 8, 3))

        result = scheduler.validate_schedule(start, end)
        assert result.is_valid is False
        assert result.uncovered_count == 1
        assert result.duplicate_count == 0

        uncovered_gaps = [g for g in result.gaps if g.is_uncovered]
        assert len(uncovered_gaps) == 1
        assert uncovered_gaps[0].shift_date == date(2026, 8, 3)

    def test_detect_multiple_uncovered_days(self):
        scheduler, staff_ids = make_scheduler_with_staff(2)
        s1, s2 = staff_ids
        start = date(2026, 9, 1)
        end = date(2026, 9, 10)

        scheduler.generate_rotation_schedule(staff_ids, start, end)

        scheduler.clear_shift(date(2026, 9, 3))
        scheduler.clear_shift(date(2026, 9, 7))
        scheduler.clear_shift(date(2026, 9, 8))

        result = scheduler.validate_schedule(start, end)
        assert result.is_valid is False
        assert result.uncovered_count == 3

    def test_validate_or_raise_uncovered(self):
        scheduler, staff_ids = make_scheduler_with_staff(2)
        s1, s2 = staff_ids
        start = date(2026, 8, 1)
        end = date(2026, 8, 5)

        scheduler.generate_rotation_schedule(staff_ids, start, end)
        scheduler.clear_shift(date(2026, 8, 3))

        with pytest.raises(UncoveredGapError):
            scheduler.validate_or_raise(start, end)


class TestExceptionGapDuplicate:
    def test_detect_duplicate_assignment(self):
        scheduler, staff_ids = make_scheduler_with_staff(3)
        s1, s2, s3 = staff_ids
        start = date(2026, 10, 1)
        end = date(2026, 10, 7)

        scheduler.generate_rotation_schedule(staff_ids, start, end)

        scheduler.set_shift(date(2026, 10, 3), s2)

        result = scheduler.validate_schedule(start, end)
        assert result.is_valid is False
        assert result.duplicate_count == 1
        assert result.uncovered_count == 0

        dup_gaps = [g for g in result.gaps if g.is_duplicate]
        assert len(dup_gaps) == 1
        assert dup_gaps[0].shift_date == date(2026, 10, 3)
        assert s3 in dup_gaps[0].staff_ids
        assert s2 in dup_gaps[0].staff_ids

    def test_validate_or_raise_duplicate(self):
        scheduler, staff_ids = make_scheduler_with_staff(2)
        s1, s2 = staff_ids
        start = date(2026, 10, 1)
        end = date(2026, 10, 5)

        scheduler.generate_rotation_schedule(staff_ids, start, end)
        scheduler.set_shift(date(2026, 10, 2), s1)

        with pytest.raises(DuplicateAssignmentError):
            scheduler.validate_or_raise(start, end)

    def test_validate_or_raise_both_gaps(self):
        scheduler, staff_ids = make_scheduler_with_staff(3)
        s1, s2, s3 = staff_ids
        start = date(2026, 11, 1)
        end = date(2026, 11, 7)

        scheduler.generate_rotation_schedule(staff_ids, start, end)

        scheduler.clear_shift(date(2026, 11, 3))
        scheduler.set_shift(date(2026, 11, 5), s1)

        with pytest.raises(OverlappingAssignmentError):
            scheduler.validate_or_raise(start, end)


class TestStaffManagement:
    def test_register_and_get_staff(self):
        scheduler = ShiftScheduler()
        sid = StaffId("alice-1")
        staff = Staff(staff_id=sid, name="Alice Wang")

        result_id = scheduler.register_staff(staff)
        assert result_id == sid

        retrieved = scheduler.get_staff(sid)
        assert retrieved is not None
        assert retrieved.name == "Alice Wang"

    def test_get_nonexistent_staff(self):
        scheduler = ShiftScheduler()
        assert scheduler.get_staff(StaffId("ghost")) is None

    def test_get_all_staff(self):
        scheduler, staff_ids = make_scheduler_with_staff(4)
        all_staff = scheduler.get_all_staff()
        assert len(all_staff) == 4

    def test_remove_staff(self):
        scheduler, staff_ids = make_scheduler_with_staff(3)
        s1 = staff_ids[0]

        assert scheduler.remove_staff(s1) is True
        assert scheduler.get_staff(s1) is None
        assert len(scheduler.get_all_staff()) == 2

    def test_remove_nonexistent_staff(self):
        scheduler = ShiftScheduler()
        assert scheduler.remove_staff(StaffId("ghost")) is False

    def test_register_duplicate_staff_id_rejected(self):
        from solocoder_py.shift_scheduler import ShiftSchedulerError

        scheduler = ShiftScheduler()
        sid = StaffId("dup")
        s1 = Staff(staff_id=sid, name="First")
        scheduler.register_staff(s1)

        s2 = Staff(staff_id=sid, name="Second")
        with pytest.raises(ShiftSchedulerError, match="already registered"):
            scheduler.register_staff(s2)


class TestScheduleGenerationErrors:
    def test_empty_staff_order_rejected(self):
        scheduler = ShiftScheduler()
        with pytest.raises(EmptyStaffListError):
            scheduler.generate_rotation_schedule(
                [], date(2026, 1, 1), date(2026, 1, 7)
            )

    def test_start_after_end_rejected(self):
        scheduler, staff_ids = make_scheduler_with_staff(3)
        with pytest.raises(InvalidDateRangeError):
            scheduler.generate_rotation_schedule(
                staff_ids, date(2026, 12, 31), date(2026, 1, 1)
            )

    def test_unregistered_staff_in_order_rejected(self):
        scheduler = ShiftScheduler()
        real_sid = StaffId("real")
        scheduler.register_staff(Staff(staff_id=real_sid, name="Real"))
        fake_sid = StaffId("fake")

        with pytest.raises(StaffNotFoundError):
            scheduler.generate_rotation_schedule(
                [real_sid, fake_sid], date(2026, 1, 1), date(2026, 1, 3)
            )

    def test_set_shift_unregistered_staff_rejected(self):
        scheduler = ShiftScheduler()
        with pytest.raises(StaffNotFoundError):
            scheduler.set_shift(date(2026, 1, 1), StaffId("ghost"))


class TestSwapRequestErrors:
    def test_create_swap_unregistered_requester(self):
        scheduler, staff_ids = make_scheduler_with_staff(2)
        s2 = staff_ids[1]
        today = date(2026, 6, 10)
        start = date(2026, 6, 15)
        end = date(2026, 6, 21)
        scheduler.generate_rotation_schedule(staff_ids, start, end)

        ghost = StaffId("ghost")
        with pytest.raises(StaffNotFoundError):
            scheduler.create_swap_request(
                requester_id=ghost,
                responder_id=s2,
                requester_date=date(2026, 6, 15),
                responder_date=date(2026, 6, 16),
                today=today,
            )

    def test_create_swap_requester_not_assigned(self):
        scheduler, staff_ids = make_scheduler_with_staff(3)
        s1, s2, s3 = staff_ids
        today = date(2026, 6, 10)
        start = date(2026, 6, 15)
        end = date(2026, 6, 21)
        scheduler.generate_rotation_schedule(staff_ids, start, end)

        with pytest.raises(ShiftNotFoundError, match="Requester"):
            scheduler.create_swap_request(
                requester_id=s1,
                responder_id=s2,
                requester_date=date(2026, 6, 17),
                responder_date=date(2026, 6, 16),
                today=today,
            )

    def test_create_swap_responder_not_assigned(self):
        scheduler, staff_ids = make_scheduler_with_staff(3)
        s1, s2, s3 = staff_ids
        today = date(2026, 6, 10)
        start = date(2026, 6, 15)
        end = date(2026, 6, 21)
        scheduler.generate_rotation_schedule(staff_ids, start, end)

        with pytest.raises(ShiftNotFoundError, match="Responder"):
            scheduler.create_swap_request(
                requester_id=s1,
                responder_id=s2,
                requester_date=date(2026, 6, 15),
                responder_date=date(2026, 6, 17),
                today=today,
            )

    def test_approve_nonexistent_swap(self):
        scheduler, staff_ids = make_scheduler_with_staff(2)
        with pytest.raises(SwapRequestNotFoundError):
            scheduler.approve_swap_request("nonexistent", staff_ids[1])

    def test_approve_already_processed(self):
        scheduler, staff_ids = make_scheduler_with_staff(3)
        s1, s2, s3 = staff_ids
        today = date(2026, 6, 10)
        start = date(2026, 6, 15)
        end = date(2026, 6, 21)
        scheduler.generate_rotation_schedule(staff_ids, start, end)

        request_id = scheduler.create_swap_request(
            requester_id=s1,
            responder_id=s2,
            requester_date=date(2026, 6, 15),
            responder_date=date(2026, 6, 16),
            today=today,
        )

        scheduler.reject_swap_request(request_id, s2)

        with pytest.raises(SwapRequestAlreadyProcessedError):
            scheduler.approve_swap_request(request_id, s2)

    def test_approve_not_authorized(self):
        scheduler, staff_ids = make_scheduler_with_staff(3)
        s1, s2, s3 = staff_ids
        today = date(2026, 6, 10)
        start = date(2026, 6, 15)
        end = date(2026, 6, 21)
        scheduler.generate_rotation_schedule(staff_ids, start, end)

        request_id = scheduler.create_swap_request(
            requester_id=s1,
            responder_id=s2,
            requester_date=date(2026, 6, 15),
            responder_date=date(2026, 6, 16),
            today=today,
        )

        with pytest.raises(SwapRequestNotAuthorizedError):
            scheduler.approve_swap_request(request_id, s1)

    def test_reject_nonexistent_swap(self):
        scheduler, staff_ids = make_scheduler_with_staff(2)
        with pytest.raises(SwapRequestNotFoundError):
            scheduler.reject_swap_request("nonexistent", staff_ids[1])

    def test_reject_already_processed(self):
        scheduler, staff_ids = make_scheduler_with_staff(3)
        s1, s2, s3 = staff_ids
        today = date(2026, 6, 10)
        start = date(2026, 6, 15)
        end = date(2026, 6, 21)
        scheduler.generate_rotation_schedule(staff_ids, start, end)

        request_id = scheduler.create_swap_request(
            requester_id=s1,
            responder_id=s2,
            requester_date=date(2026, 6, 15),
            responder_date=date(2026, 6, 16),
            today=today,
        )

        scheduler.approve_swap_request(request_id, s2)

        with pytest.raises(SwapRequestAlreadyProcessedError):
            scheduler.reject_swap_request(request_id, s2)


class TestScheduleQueries:
    def test_get_schedule_range(self):
        scheduler, staff_ids = make_scheduler_with_staff(2)
        s1, s2 = staff_ids
        start = date(2026, 3, 1)
        end = date(2026, 3, 4)

        scheduler.generate_rotation_schedule(staff_ids, start, end)

        range_result = scheduler.get_schedule_range(date(2026, 3, 2), date(2026, 3, 3))
        assert len(range_result) == 2
        assert range_result[date(2026, 3, 2)] == [s2]
        assert range_result[date(2026, 3, 3)] == [s1]

    def test_get_schedule_range_empty(self):
        scheduler, staff_ids = make_scheduler_with_staff(2)
        scheduler.generate_rotation_schedule(staff_ids, date(2026, 1, 1), date(2026, 1, 7))

        range_result = scheduler.get_schedule_range(date(2026, 2, 1), date(2026, 2, 3))
        for d, assignments in range_result.items():
            assert assignments == []

    def test_get_schedule_range_invalid_dates(self):
        scheduler = ShiftScheduler()
        with pytest.raises(InvalidDateRangeError):
            scheduler.get_schedule_range(date(2026, 12, 31), date(2026, 1, 1))

    def test_clear_shift_nonexistent(self):
        scheduler = ShiftScheduler()
        assert scheduler.clear_shift(date(2026, 1, 1)) is False

    def test_clear_specific_staff(self):
        scheduler, staff_ids = make_scheduler_with_staff(2)
        s1, s2 = staff_ids
        start = date(2026, 5, 1)
        end = date(2026, 5, 3)

        scheduler.generate_rotation_schedule(staff_ids, start, end)
        scheduler.set_shift(date(2026, 5, 2), s1)

        assert len(scheduler.get_assignment(date(2026, 5, 2))) == 2

        assert scheduler.clear_shift(date(2026, 5, 2), s2) is True
        assert scheduler.get_assignment(date(2026, 5, 2)) == [s1]


class TestClearOperations:
    def test_clear_schedule(self):
        scheduler, staff_ids = make_scheduler_with_staff(3)
        scheduler.generate_rotation_schedule(
            staff_ids, date(2026, 1, 1), date(2026, 1, 31)
        )
        assert len(scheduler.get_schedule_range(date(2026, 1, 1), date(2026, 1, 31))) == 31

        scheduler.clear_schedule()
        result = scheduler.validate_schedule()
        assert result.is_valid is True

    def test_clear_swap_requests(self):
        scheduler, staff_ids = make_scheduler_with_staff(3)
        s1, s2, s3 = staff_ids
        today = date(2026, 6, 10)
        scheduler.generate_rotation_schedule(
            staff_ids, date(2026, 6, 15), date(2026, 6, 30)
        )

        scheduler.create_swap_request(
            s1, s2, date(2026, 6, 15), date(2026, 6, 16), today=today
        )
        scheduler.create_swap_request(
            s2, s3, date(2026, 6, 16), date(2026, 6, 17), today=today
        )

        assert len(scheduler.get_all_swap_requests()) == 2

        scheduler.clear_swap_requests()
        assert len(scheduler.get_all_swap_requests()) == 0


class TestGetAllSwapRequests:
    def test_list_all_swap_requests(self):
        scheduler, staff_ids = make_scheduler_with_staff(3)
        s1, s2, s3 = staff_ids
        today = date(2026, 6, 10)
        scheduler.generate_rotation_schedule(
            staff_ids, date(2026, 6, 15), date(2026, 6, 30)
        )

        rid1 = scheduler.create_swap_request(
            s1, s2, date(2026, 6, 15), date(2026, 6, 16), today=today
        )
        rid2 = scheduler.create_swap_request(
            s2, s3, date(2026, 6, 16), date(2026, 6, 17), today=today
        )

        scheduler.approve_swap_request(rid1, s2)

        all_swaps = scheduler.get_all_swap_requests()
        assert len(all_swaps) == 2
        statuses = {sw.request_id: sw.status for sw in all_swaps}
        assert statuses[rid1] == SwapRequestStatus.EFFECTIVE
        assert statuses[rid2] == SwapRequestStatus.PENDING


class TestSameDateSwap:
    def test_swap_same_date_requires_both_assigned(self):
        scheduler, staff_ids = make_scheduler_with_staff(4)
        s1, s2, s3, s4 = staff_ids
        today = date(2026, 6, 10)
        start = date(2026, 6, 15)
        end = date(2026, 6, 18)

        scheduler.generate_rotation_schedule(staff_ids, start, end)

        assert scheduler.get_assignment(date(2026, 6, 15)) == [s1]
        assert scheduler.get_assignment(date(2026, 6, 16)) == [s2]
        assert scheduler.get_assignment(date(2026, 6, 17)) == [s3]

        with pytest.raises(ShiftNotFoundError, match="Responder"):
            scheduler.create_swap_request(
                requester_id=s1,
                responder_id=s2,
                requester_date=date(2026, 6, 15),
                responder_date=date(2026, 6, 15),
                today=today,
            )

        request_id = scheduler.create_swap_request(
            requester_id=s1,
            responder_id=s3,
            requester_date=date(2026, 6, 15),
            responder_date=date(2026, 6, 17),
            today=today,
        )

        assert request_id is not None
        swap = scheduler.get_swap_request(request_id)
        assert swap.is_pending is True
