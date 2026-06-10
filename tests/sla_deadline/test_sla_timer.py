from datetime import date, datetime, timedelta

import pytest

from solocoder_py.sla_deadline import (
    InvalidSlaDurationError,
    InvalidWorkCalendarError,
    SlaTimer,
    SlaTimerAlreadyStartedError,
    SlaTimerExpiredError,
    SlaTimerNotPausedError,
    SlaTimerNotRunningError,
    SlaTimerNotStartedError,
    SlaTimerStatus,
)
from solocoder_py.work_calendar import WorkCalendar

from tests.sla_deadline.conftest import (
    make_calendar_with_custom_schedule,
    make_calendar_with_holidays,
    make_default_calendar,
    make_default_sla_timer,
    make_friday_6pm,
    make_monday_1030am,
    make_monday_10am,
    make_monday_1130am,
    make_monday_11am,
    make_monday_12pm,
    make_monday_1pm,
    make_monday_3pm,
    make_monday_4pm,
    make_monday_6pm,
    make_monday_930am,
    make_monday_9am,
    make_monday_next_week_9am,
    make_saturday_9am,
    make_sla_timer_with_calendar,
    make_tuesday_9am,
)


class TestSlaTimerInitialization:
    def test_valid_initialization(self):
        timer = SlaTimer(total_work_hours=8.0)
        assert timer.total_work_hours == 8.0
        assert timer.status == SlaTimerStatus.NOT_STARTED
        assert timer.start_time is None
        assert timer.is_started is False
        assert timer.is_running is False
        assert timer.is_paused is False
        assert timer.is_expired is False

    def test_custom_work_calendar(self):
        calendar = make_default_calendar()
        timer = SlaTimer(total_work_hours=8.0, work_calendar=calendar)
        assert timer.work_calendar == calendar

    def test_invalid_duration_raises_error(self):
        with pytest.raises(InvalidSlaDurationError):
            SlaTimer(total_work_hours=0)

        with pytest.raises(InvalidSlaDurationError):
            SlaTimer(total_work_hours=-5.0)

    def test_invalid_calendar_raises_error(self):
        with pytest.raises(InvalidWorkCalendarError):
            SlaTimer(total_work_hours=8.0, work_calendar="not a calendar")


class TestSlaTimerStart:
    def test_start_sets_status_to_running(self):
        timer = make_default_sla_timer()
        start_time = make_monday_9am()
        timer.start(start_time=start_time)

        assert timer.status == SlaTimerStatus.RUNNING
        assert timer.start_time == start_time
        assert timer.is_started is True
        assert timer.is_running is True
        assert timer.is_paused is False
        assert timer.is_expired is False

    def test_start_without_time_uses_current_time(self):
        timer = make_default_sla_timer()
        timer.start()

        assert timer.start_time is not None
        assert timer.status == SlaTimerStatus.RUNNING

    def test_start_already_started_raises_error(self):
        timer = make_default_sla_timer()
        timer.start(start_time=make_monday_9am())

        with pytest.raises(SlaTimerAlreadyStartedError):
            timer.start(start_time=make_monday_10am())

    def test_start_paused_timer_raises_error(self):
        timer = make_default_sla_timer()
        timer.start(start_time=make_monday_9am())
        timer.pause(pause_time=make_monday_10am())

        with pytest.raises(SlaTimerAlreadyStartedError):
            timer.start(start_time=make_monday_11am())


class TestSlaTimerPause:
    def test_pause_running_timer(self):
        timer = make_default_sla_timer()
        timer.start(start_time=make_monday_9am())
        timer.pause(pause_time=make_monday_10am())

        assert timer.status == SlaTimerStatus.PAUSED
        assert timer.is_paused is True
        assert timer.is_running is False
        assert len(timer.pause_records) == 1
        assert timer.pause_records[0].pause_time == make_monday_10am()
        assert timer.pause_records[0].resume_time is None
        assert timer.pause_records[0].is_active is True

    def test_pause_not_started_raises_error(self):
        timer = make_default_sla_timer()

        with pytest.raises(SlaTimerNotStartedError):
            timer.pause(pause_time=make_monday_10am())

    def test_pause_already_paused_raises_error(self):
        timer = make_default_sla_timer()
        timer.start(start_time=make_monday_9am())
        timer.pause(pause_time=make_monday_10am())

        with pytest.raises(SlaTimerNotRunningError):
            timer.pause(pause_time=make_monday_11am())

    def test_pause_expired_timer_raises_error(self):
        timer = make_default_sla_timer(total_work_hours=1.0)
        timer.start(start_time=make_monday_9am())

        with pytest.raises(SlaTimerExpiredError):
            timer.pause(pause_time=make_monday_11am())


class TestSlaTimerResume:
    def test_resume_paused_timer(self):
        timer = make_default_sla_timer()
        timer.start(start_time=make_monday_9am())
        timer.pause(pause_time=make_monday_10am())
        timer.resume(resume_time=make_monday_11am())

        assert timer.status == SlaTimerStatus.RUNNING
        assert timer.is_running is True
        assert timer.is_paused is False
        assert len(timer.pause_records) == 1
        assert timer.pause_records[0].resume_time == make_monday_11am()
        assert timer.pause_records[0].is_active is False

    def test_resume_not_started_raises_error(self):
        timer = make_default_sla_timer()

        with pytest.raises(SlaTimerNotStartedError):
            timer.resume(resume_time=make_monday_10am())

    def test_resume_running_raises_error(self):
        timer = make_default_sla_timer()
        timer.start(start_time=make_monday_9am())

        with pytest.raises(SlaTimerNotPausedError):
            timer.resume(resume_time=make_monday_10am())

    def test_resume_expired_raises_error(self):
        timer = make_default_sla_timer(total_work_hours=1.0)
        timer.start(start_time=make_monday_9am())
        timer.pause(pause_time=make_monday_930am())

        timer._status = SlaTimerStatus.EXPIRED

        with pytest.raises(SlaTimerExpiredError):
            timer.resume(resume_time=make_monday_11am())


class TestSlaTimerWorkHoursCalculation:
    def test_same_morning_period(self):
        timer = make_default_sla_timer()
        start = make_monday_9am()
        end = datetime(2024, 1, 15, 11, 0, 0)

        hours = timer._calculate_work_hours_between(start, end)
        assert hours == 2.0

    def test_morning_to_afternoon_with_lunch_break(self):
        timer = make_default_sla_timer()
        start = make_monday_11am()
        end = datetime(2024, 1, 15, 14, 0, 0)

        hours = timer._calculate_work_hours_between(start, end)
        assert hours == 2.0

    def test_across_multiple_days(self):
        timer = make_default_sla_timer()
        start = make_monday_9am()
        end = make_tuesday_9am()

        hours = timer._calculate_work_hours_between(start, end)
        assert hours == 8.0

    def test_weekend_skipped(self):
        timer = make_default_sla_timer()
        start = make_friday_6pm() - timedelta(hours=1)
        end = make_monday_next_week_9am()

        hours = timer._calculate_work_hours_between(start, end)
        assert hours == 1.0

    def test_holiday_skipped(self):
        holidays = [date(2024, 1, 16)]
        calendar = make_calendar_with_holidays(holidays)
        timer = make_sla_timer_with_calendar(8.0, calendar)

        start = make_monday_9am()
        end = make_monday_next_week_9am()

        hours = timer._calculate_work_hours_between(start, end)
        assert hours == 32.0

    def test_non_work_hours_skipped(self):
        timer = make_default_sla_timer()
        start = datetime(2024, 1, 15, 7, 0, 0)
        end = datetime(2024, 1, 15, 20, 0, 0)

        hours = timer._calculate_work_hours_between(start, end)
        assert hours == 8.0

    def test_end_before_start_returns_zero(self):
        timer = make_default_sla_timer()
        start = make_monday_10am()
        end = make_monday_9am()

        hours = timer._calculate_work_hours_between(start, end)
        assert hours == 0.0

    def test_custom_work_schedule(self):
        calendar = make_calendar_with_custom_schedule(
            morning_start=8, morning_end=12, afternoon_start=13, afternoon_end=17
        )
        timer = make_sla_timer_with_calendar(8.0, calendar)

        start = datetime(2024, 1, 15, 8, 0, 0)
        end = datetime(2024, 1, 15, 17, 0, 0)

        hours = timer._calculate_work_hours_between(start, end)
        assert hours == 8.0


class TestSlaTimerNormalFlow:
    def test_full_day_sla_completion(self):
        timer = make_default_sla_timer(total_work_hours=8.0)
        timer.start(start_time=make_monday_9am())

        status = timer.get_status(current_time=make_monday_6pm())

        assert status.is_expired is True
        assert status.elapsed_work_hours == 8.0
        assert status.remaining_work_hours == 0.0
        assert status.total_work_hours == 8.0
        assert status.status == SlaTimerStatus.EXPIRED
        assert status.estimated_deadline == make_monday_6pm()

    def test_half_day_progress(self):
        timer = make_default_sla_timer(total_work_hours=8.0)
        timer.start(start_time=make_monday_9am())

        status = timer.get_status(current_time=make_monday_1pm())

        assert status.is_expired is False
        assert status.elapsed_work_hours == 3.0
        assert status.remaining_work_hours == 5.0
        assert status.progress_percentage == 37.5

    def test_partial_morning_hours(self):
        timer = make_default_sla_timer(total_work_hours=2.0)
        timer.start(start_time=make_monday_10am())

        status = timer.get_status(current_time=make_monday_12pm())

        assert status.is_expired is True
        assert status.elapsed_work_hours == 2.0
        assert status.remaining_work_hours == 0.0

    def test_sla_crossing_lunch_break(self):
        timer = make_default_sla_timer(total_work_hours=2.0)
        timer.start(start_time=make_monday_11am())

        status = timer.get_status(current_time=make_monday_1pm())
        assert status.is_expired is False
        assert status.elapsed_work_hours == 1.0
        assert status.remaining_work_hours == 1.0

        status = timer.get_status(current_time=datetime(2024, 1, 15, 14, 0, 0))
        assert status.is_expired is True
        assert status.elapsed_work_hours == 2.0
        assert status.remaining_work_hours == 0.0

    def test_sla_crossing_multiple_days(self):
        timer = make_default_sla_timer(total_work_hours=12.0)
        timer.start(start_time=make_monday_9am())

        status = timer.get_status(current_time=make_monday_6pm())

        assert status.is_expired is False
        assert status.elapsed_work_hours == 8.0
        assert status.remaining_work_hours == 4.0

        status = timer.get_status(current_time=datetime(2024, 1, 16, 13, 0, 0))
        assert status.is_expired is False
        assert status.elapsed_work_hours == 11.0
        assert status.remaining_work_hours == 1.0

        status = timer.get_status(current_time=datetime(2024, 1, 16, 14, 0, 0))
        assert status.is_expired is True
        assert status.elapsed_work_hours == 12.0
        assert status.remaining_work_hours == 0.0
        assert status.estimated_deadline == datetime(2024, 1, 16, 14, 0, 0)

    def test_sla_starting_in_non_work_hours(self):
        timer = make_default_sla_timer(total_work_hours=2.0)
        timer.start(start_time=datetime(2024, 1, 15, 7, 0, 0))

        status = timer.get_status(current_time=make_monday_11am())

        assert status.elapsed_work_hours == 2.0
        assert status.is_expired is True


class TestSlaTimerPauseResume:
    def test_single_pause_resume(self):
        timer = make_default_sla_timer(total_work_hours=4.0)
        timer.start(start_time=make_monday_9am())

        timer.pause(pause_time=make_monday_10am())
        status_paused = timer.get_status(current_time=make_monday_11am())
        assert status_paused.elapsed_work_hours == 1.0
        assert status_paused.status == SlaTimerStatus.PAUSED

        timer.resume(resume_time=make_monday_1pm())
        status_resumed = timer.get_status(current_time=make_monday_1pm())
        assert status_resumed.elapsed_work_hours == 1.0
        assert status_resumed.remaining_work_hours == 3.0

        status_final = timer.get_status(current_time=datetime(2024, 1, 15, 16, 0, 0))
        assert status_final.elapsed_work_hours == 4.0
        assert status_final.is_expired is True

    def test_multiple_pause_resume(self):
        timer = make_default_sla_timer(total_work_hours=6.0)
        timer.start(start_time=make_monday_9am())

        timer.pause(pause_time=make_monday_10am())
        timer.resume(resume_time=make_monday_11am())

        timer.pause(pause_time=make_monday_12pm())
        timer.resume(resume_time=make_monday_1pm())

        status = timer.get_status(current_time=datetime(2024, 1, 15, 14, 0, 0))

        assert status.elapsed_work_hours == 3.0
        assert status.remaining_work_hours == 3.0

        status_final = timer.get_status(current_time=datetime(2024, 1, 15, 17, 0, 0))
        assert status_final.elapsed_work_hours == 6.0
        assert status_final.is_expired is True

    def test_pause_during_non_work_hours(self):
        timer = make_default_sla_timer(total_work_hours=4.0)
        timer.start(start_time=make_monday_9am())

        timer.pause(pause_time=make_monday_12pm())
        timer.resume(resume_time=make_monday_6pm())

        status = timer.get_status(current_time=datetime(2024, 1, 16, 10, 0, 0))

        assert status.elapsed_work_hours == 4.0
        assert status.is_expired is True

    def test_pause_across_weekend(self):
        timer = make_default_sla_timer(total_work_hours=5.0)
        timer.start(start_time=make_monday_9am())

        timer.pause(pause_time=make_monday_10am())
        timer.resume(resume_time=make_monday_next_week_9am())

        status = timer.get_status(current_time=datetime(2024, 1, 22, 13, 0, 0))
        assert status.elapsed_work_hours == 4.0
        assert status.is_expired is False

        status = timer.get_status(current_time=datetime(2024, 1, 22, 14, 0, 0))
        assert status.elapsed_work_hours == 5.0
        assert status.is_expired is True

    def test_pause_record_correctness(self):
        timer = make_default_sla_timer(total_work_hours=8.0)
        timer.start(start_time=make_monday_9am())

        timer.pause(pause_time=make_monday_10am())
        timer.resume(resume_time=make_monday_11am())

        timer.pause(pause_time=make_monday_12pm())
        timer.resume(resume_time=make_monday_1pm())

        records = timer.pause_records
        assert len(records) == 2
        assert records[0].pause_time == make_monday_10am()
        assert records[0].resume_time == make_monday_11am()
        assert records[0].pause_duration_seconds == 3600.0
        assert records[1].pause_time == make_monday_12pm()
        assert records[1].resume_time == make_monday_1pm()
        assert records[1].pause_duration_seconds == 3600.0

    def test_active_pause_record(self):
        timer = make_default_sla_timer()
        timer.start(start_time=make_monday_9am())
        timer.pause(pause_time=make_monday_10am())

        assert timer.pause_records[0].is_active is True
        assert timer.pause_records[0].pause_duration_seconds == 0.0


class TestSlaTimerBoundaryConditions:
    def test_sla_span_exactly_lunch_break(self):
        timer = make_default_sla_timer(total_work_hours=3.0)
        timer.start(start_time=make_monday_11am())

        status = timer.get_status(current_time=make_monday_3pm())

        assert status.elapsed_work_hours == 3.0
        assert status.is_expired is True
        assert status.estimated_deadline == datetime(2024, 1, 15, 15, 0, 0)

    def test_sla_deadline_on_non_workday(self):
        timer = make_default_sla_timer(total_work_hours=24.0)
        timer.start(start_time=datetime(2024, 1, 17, 9, 0, 0))

        status = timer.get_status(current_time=make_friday_6pm())

        assert status.elapsed_work_hours == 24.0
        assert status.remaining_work_hours == 0.0
        assert status.is_expired is True
        assert status.estimated_deadline == make_friday_6pm()
        assert status.estimated_deadline.weekday() == 4

        status_saturday = timer.get_status(current_time=make_saturday_9am())
        assert status_saturday.is_expired is True
        assert status_saturday.elapsed_work_hours == 24.0

    def test_sla_start_on_weekend(self):
        timer = make_default_sla_timer(total_work_hours=8.0)
        timer.start(start_time=make_saturday_9am())

        status = timer.get_status(current_time=make_monday_next_week_9am())

        assert status.elapsed_work_hours == 0.0
        assert status.remaining_work_hours == 8.0

        status = timer.get_status(current_time=datetime(2024, 1, 22, 18, 0, 0))
        assert status.elapsed_work_hours == 8.0
        assert status.is_expired is True

    def test_sla_start_on_holiday(self):
        holidays = [date(2024, 1, 15)]
        calendar = make_calendar_with_holidays(holidays)
        timer = make_sla_timer_with_calendar(8.0, calendar)

        timer.start(start_time=make_monday_9am())

        status = timer.get_status(current_time=make_monday_6pm())
        assert status.elapsed_work_hours == 0.0

        status = timer.get_status(current_time=make_tuesday_9am() + timedelta(hours=8))
        assert status.elapsed_work_hours == 7.0
        assert status.is_expired is False

        status = timer.get_status(current_time=make_tuesday_9am() + timedelta(hours=9))
        assert status.elapsed_work_hours == 8.0
        assert status.is_expired is True

    def test_multiple_pause_resume_consistency(self):
        timer = make_default_sla_timer(total_work_hours=10.0)
        timer.start(start_time=make_monday_9am())

        checkpoints = []

        timer.pause(pause_time=make_monday_10am())
        checkpoints.append(timer.get_status(current_time=make_monday_10am()).elapsed_work_hours)

        timer.resume(resume_time=make_monday_1030am())
        checkpoints.append(timer.get_status(current_time=make_monday_1030am()).elapsed_work_hours)

        timer.pause(pause_time=make_monday_1130am())
        checkpoints.append(timer.get_status(current_time=make_monday_1130am()).elapsed_work_hours)

        timer.resume(resume_time=make_monday_1pm())
        checkpoints.append(timer.get_status(current_time=make_monday_1pm()).elapsed_work_hours)

        timer.pause(pause_time=make_monday_3pm())
        checkpoints.append(timer.get_status(current_time=make_monday_3pm()).elapsed_work_hours)

        timer.resume(resume_time=make_monday_4pm())
        checkpoints.append(timer.get_status(current_time=make_monday_4pm()).elapsed_work_hours)

        assert checkpoints == [1.0, 1.0, 2.0, 2.0, 4.0, 4.0]

        status_final = timer.get_status(current_time=make_monday_6pm())
        assert status_final.elapsed_work_hours == 6.0
        assert status_final.remaining_work_hours == 4.0

    def test_very_short_sla_duration(self):
        timer = make_default_sla_timer(total_work_hours=0.5)
        timer.start(start_time=make_monday_9am())

        status = timer.get_status(current_time=datetime(2024, 1, 15, 9, 30, 0))
        assert status.elapsed_work_hours == 0.5
        assert status.is_expired is True

    def test_long_sla_duration(self):
        timer = make_default_sla_timer(total_work_hours=160.0)
        timer.start(start_time=make_monday_9am())

        status = timer.get_status(current_time=make_monday_6pm())
        assert status.elapsed_work_hours == 8.0
        assert status.remaining_work_hours == 152.0

        expected_deadline = timer.work_calendar.add_work_hours(make_monday_6pm(), 152.0)
        assert status.estimated_deadline == expected_deadline


class TestSlaTimerErrorConditions:
    def test_get_status_before_start_raises_error(self):
        timer = make_default_sla_timer()

        with pytest.raises(SlaTimerNotStartedError):
            timer.get_status()

    def test_query_after_deadline(self):
        timer = make_default_sla_timer(total_work_hours=1.0)
        timer.start(start_time=make_monday_9am())

        status = timer.get_status(current_time=make_monday_6pm())

        assert status.is_expired is True
        assert status.elapsed_work_hours == 1.0
        assert status.remaining_work_hours == 0.0
        assert status.status == SlaTimerStatus.EXPIRED

    def test_pause_before_start_raises_error(self):
        timer = make_default_sla_timer()

        with pytest.raises(SlaTimerNotStartedError):
            timer.pause()

    def test_resume_before_start_raises_error(self):
        timer = make_default_sla_timer()

        with pytest.raises(SlaTimerNotStartedError):
            timer.resume()

    def test_resume_without_pause_raises_error(self):
        timer = make_default_sla_timer()
        timer.start(start_time=make_monday_9am())

        with pytest.raises(SlaTimerNotPausedError):
            timer.resume()

    def test_very_long_pause(self):
        timer = make_default_sla_timer(total_work_hours=4.0)
        timer.start(start_time=make_monday_9am())

        timer.pause(pause_time=make_monday_10am())

        one_year_later = datetime(2025, 1, 15, 9, 0, 0)
        status_paused = timer.get_status(current_time=one_year_later)

        assert status_paused.elapsed_work_hours == 1.0
        assert status_paused.status == SlaTimerStatus.PAUSED
        assert status_paused.is_expired is False

        timer.resume(resume_time=one_year_later)

        status_resumed = timer.get_status(current_time=one_year_later + timedelta(hours=3))
        assert status_resumed.elapsed_work_hours == 4.0
        assert status_resumed.is_expired is True

    def test_starting_at_exactly_deadline(self):
        timer = make_default_sla_timer(total_work_hours=8.0)
        timer.start(start_time=make_monday_9am())

        status = timer.get_status(current_time=make_monday_6pm())
        assert status.is_expired is True
        assert status.estimated_deadline == make_monday_6pm()

    def test_pause_at_exactly_deadline(self):
        timer = make_default_sla_timer(total_work_hours=3.0)
        timer.start(start_time=make_monday_9am())

        with pytest.raises(SlaTimerExpiredError):
            timer.pause(pause_time=make_monday_1pm())


class TestSlaTimerWorkCalendarIntegration:
    def test_custom_work_hours(self):
        calendar = make_calendar_with_custom_schedule(
            morning_start=10, morning_end=14, afternoon_start=15, afternoon_end=19
        )
        timer = make_sla_timer_with_calendar(8.0, calendar)

        timer.start(start_time=datetime(2024, 1, 15, 10, 0, 0))

        status = timer.get_status(current_time=datetime(2024, 1, 15, 19, 0, 0))
        assert status.elapsed_work_hours == 8.0
        assert status.is_expired is True

    def test_no_lunch_break(self):
        calendar = WorkCalendar()
        from datetime import time
        from solocoder_py.work_calendar import WorkDaySchedule, WorkTimeRange

        schedule = WorkDaySchedule(
            morning=WorkTimeRange(time(9, 0), time(17, 0)),
            afternoon=WorkTimeRange(time(17, 0), time(17, 1)),
        )
        calendar.set_work_schedule(schedule)

        timer = make_sla_timer_with_calendar(8.0, calendar)

        timer.start(start_time=datetime(2024, 1, 15, 9, 0, 0))

        status = timer.get_status(current_time=datetime(2024, 1, 15, 17, 0, 0))
        assert status.elapsed_work_hours == 8.0
        assert status.is_expired is True

    def test_complex_holiday_schedule(self):
        holidays = [
            date(2024, 1, 15),
            date(2024, 1, 16),
            date(2024, 1, 17),
        ]
        calendar = make_calendar_with_holidays(holidays)
        timer = make_sla_timer_with_calendar(8.0, calendar)

        timer.start(start_time=make_monday_9am())

        status = timer.get_status(current_time=datetime(2024, 1, 17, 18, 0, 0))
        assert status.elapsed_work_hours == 0.0

        status = timer.get_status(current_time=datetime(2024, 1, 18, 18, 0, 0))
        assert status.elapsed_work_hours == 8.0
        assert status.is_expired is True

    def test_workday_override(self):
        from solocoder_py.work_calendar import CalendarConfig

        config = CalendarConfig(
            holidays=frozenset([date(2024, 1, 15)]),
            workdays=frozenset([date(2024, 1, 20)]),
        )
        calendar = WorkCalendar(config=config)
        timer = make_sla_timer_with_calendar(8.0, calendar)

        timer.start(start_time=make_monday_9am())

        status = timer.get_status(current_time=make_monday_6pm())
        assert status.elapsed_work_hours == 0.0

        timer2 = make_sla_timer_with_calendar(8.0, calendar)
        timer2.start(start_time=make_saturday_9am())

        status2 = timer2.get_status(current_time=make_saturday_9am() + timedelta(hours=9))
        assert status2.elapsed_work_hours == 8.0
        assert status2.is_expired is True


class TestSlaTimerResult:
    def test_progress_percentage(self):
        from solocoder_py.sla_deadline import SlaTimerResult

        result = SlaTimerResult(
            total_work_hours=8.0,
            elapsed_work_hours=4.0,
            remaining_work_hours=4.0,
            estimated_deadline=make_monday_6pm(),
            is_expired=False,
            status=SlaTimerStatus.RUNNING,
            current_time=make_monday_1pm(),
        )

        assert result.progress_percentage == 50.0

    def test_progress_percentage_expired(self):
        from solocoder_py.sla_deadline import SlaTimerResult

        result = SlaTimerResult(
            total_work_hours=8.0,
            elapsed_work_hours=8.0,
            remaining_work_hours=0.0,
            estimated_deadline=make_monday_6pm(),
            is_expired=True,
            status=SlaTimerStatus.EXPIRED,
            current_time=make_monday_6pm(),
        )

        assert result.progress_percentage == 100.0

    def test_progress_percentage_overtime(self):
        from solocoder_py.sla_deadline import SlaTimerResult

        result = SlaTimerResult(
            total_work_hours=8.0,
            elapsed_work_hours=10.0,
            remaining_work_hours=0.0,
            estimated_deadline=make_monday_6pm(),
            is_expired=True,
            status=SlaTimerStatus.EXPIRED,
            current_time=make_monday_6pm() + timedelta(hours=2),
        )

        assert result.progress_percentage == 100.0

    def test_progress_percentage_zero_duration(self):
        from solocoder_py.sla_deadline import SlaTimerResult

        result = SlaTimerResult(
            total_work_hours=0.0,
            elapsed_work_hours=0.0,
            remaining_work_hours=0.0,
            estimated_deadline=make_monday_9am(),
            is_expired=False,
            status=SlaTimerStatus.RUNNING,
            current_time=make_monday_9am(),
        )

        assert result.progress_percentage == 0.0


class TestSlaTimerAdditionalEdgeCases:
    def test_sla_crossing_multiple_weekends_and_holidays(self):
        holidays = [date(2024, 1, 18), date(2024, 1, 25)]
        calendar = make_calendar_with_holidays(holidays)
        timer = make_sla_timer_with_calendar(40.0, calendar)

        timer.start(start_time=make_monday_9am())

        status = timer.get_status(current_time=datetime(2024, 1, 15, 18, 0, 0))
        assert status.elapsed_work_hours == 8.0
        assert status.remaining_work_hours == 32.0

        status = timer.get_status(current_time=datetime(2024, 2, 1, 18, 0, 0))
        assert status.elapsed_work_hours == 40.0
        assert status.is_expired is True

    def test_pause_and_resume_during_non_work_hours(self):
        timer = make_default_sla_timer(total_work_hours=4.0)
        timer.start(start_time=make_monday_9am())

        timer.pause(pause_time=make_monday_12pm())
        status_paused = timer.get_status(current_time=datetime(2024, 1, 15, 20, 0, 0))
        assert status_paused.elapsed_work_hours == 3.0
        assert status_paused.status == SlaTimerStatus.PAUSED

        timer.resume(resume_time=datetime(2024, 1, 15, 20, 0, 0))
        status_resumed = timer.get_status(current_time=make_tuesday_9am())
        assert status_resumed.elapsed_work_hours == 3.0
        assert status_resumed.remaining_work_hours == 1.0

        status_final = timer.get_status(current_time=datetime(2024, 1, 16, 10, 0, 0))
        assert status_final.elapsed_work_hours == 4.0
        assert status_final.is_expired is True

    def test_get_status_consistency_across_states(self):
        timer = make_default_sla_timer(total_work_hours=5.0)
        timer.start(start_time=make_monday_9am())

        status_running = timer.get_status(current_time=make_monday_10am())
        assert status_running.status == SlaTimerStatus.RUNNING
        assert status_running.elapsed_work_hours == 1.0

        timer.pause(pause_time=make_monday_10am())
        status_paused = timer.get_status(current_time=make_monday_12pm())
        assert status_paused.status == SlaTimerStatus.PAUSED
        assert status_paused.elapsed_work_hours == 1.0

        timer.resume(resume_time=make_monday_1pm())
        status_resumed = timer.get_status(current_time=make_monday_1pm())
        assert status_resumed.status == SlaTimerStatus.RUNNING
        assert status_resumed.elapsed_work_hours == 1.0

        status_final = timer.get_status(current_time=datetime(2024, 1, 15, 17, 0, 0))
        assert status_final.status == SlaTimerStatus.EXPIRED
        assert status_final.elapsed_work_hours == 5.0

    def test_sla_deadline_estimation_accuracy(self):
        timer = make_default_sla_timer(total_work_hours=16.0)
        timer.start(start_time=make_monday_9am())

        status = timer.get_status(current_time=make_monday_10am())
        expected_deadline = timer.work_calendar.add_work_hours(make_monday_10am(), 15.0)
        assert status.estimated_deadline == expected_deadline
        assert status.remaining_work_hours == 15.0

    def test_multiple_rapid_pause_resume(self):
        timer = make_default_sla_timer(total_work_hours=3.0)
        timer.start(start_time=make_monday_9am())

        for i in range(5):
            check_time = make_monday_9am() + timedelta(minutes=30 + i * 10)
            timer.pause(pause_time=check_time)
            timer.resume(resume_time=check_time + timedelta(minutes=1))

        status = timer.get_status(current_time=make_monday_12pm())
        expected_hours = 3.0 - (5 * 1 / 60.0)
        assert abs(status.elapsed_work_hours - expected_hours) < 0.01
        assert status.is_expired is False
        assert len(timer.pause_records) == 5

    def test_sla_start_at_exact_work_period_boundary(self):
        timer = make_default_sla_timer(total_work_hours=3.0)
        timer.start(start_time=make_monday_12pm())

        status = timer.get_status(current_time=make_monday_1pm())
        assert status.elapsed_work_hours == 0.0

        status = timer.get_status(current_time=datetime(2024, 1, 15, 16, 0, 0))
        assert status.elapsed_work_hours == 3.0
        assert status.is_expired is True

    def test_pause_at_exact_work_period_boundary(self):
        timer = make_default_sla_timer(total_work_hours=5.0)
        timer.start(start_time=make_monday_9am())

        timer.pause(pause_time=make_monday_12pm())
        status = timer.get_status(current_time=make_monday_1pm())
        assert status.elapsed_work_hours == 3.0
        assert status.status == SlaTimerStatus.PAUSED

        timer.resume(resume_time=make_monday_1pm())
        status = timer.get_status(current_time=datetime(2024, 1, 15, 15, 0, 0))
        assert status.elapsed_work_hours == 5.0
        assert status.is_expired is True


class TestSlaTimerAdditionalErrorConditions:
    def test_negative_work_hours_in_result(self):
        from solocoder_py.sla_deadline import SlaTimerResult

        result = SlaTimerResult(
            total_work_hours=8.0,
            elapsed_work_hours=10.0,
            remaining_work_hours=-2.0,
            estimated_deadline=make_monday_6pm(),
            is_expired=True,
            status=SlaTimerStatus.EXPIRED,
            current_time=make_monday_6pm(),
        )
        assert result.remaining_work_hours == -2.0
        assert result.progress_percentage == 100.0

    def test_get_status_repeatedly_after_expiration(self):
        timer = make_default_sla_timer(total_work_hours=1.0)
        timer.start(start_time=make_monday_9am())

        status1 = timer.get_status(current_time=make_monday_11am())
        assert status1.is_expired is True

        status2 = timer.get_status(current_time=make_tuesday_9am())
        assert status2.is_expired is True
        assert status2.elapsed_work_hours == 1.0
        assert status2.remaining_work_hours == 0.0

    def test_pause_resume_idempotency(self):
        timer = make_default_sla_timer(total_work_hours=4.0)
        timer.start(start_time=make_monday_9am())

        timer.pause(pause_time=make_monday_10am())
        elapsed1 = timer.get_status(current_time=make_monday_10am()).elapsed_work_hours

        with pytest.raises(SlaTimerNotRunningError):
            timer.pause(pause_time=make_monday_10am())

        timer.resume(resume_time=make_monday_11am())
        elapsed2 = timer.get_status(current_time=make_monday_11am()).elapsed_work_hours
        assert elapsed1 == elapsed2

        with pytest.raises(SlaTimerNotPausedError):
            timer.resume(resume_time=make_monday_11am())

    def test_sla_with_fractional_hours(self):
        timer = make_default_sla_timer(total_work_hours=2.5)
        timer.start(start_time=make_monday_9am())

        status = timer.get_status(current_time=datetime(2024, 1, 15, 11, 30, 0))
        assert status.elapsed_work_hours == 2.5
        assert status.is_expired is True

    def test_estimated_deadline_on_holiday(self):
        holidays = [date(2024, 1, 16)]
        calendar = make_calendar_with_holidays(holidays)
        timer = make_sla_timer_with_calendar(12.0, calendar)

        timer.start(start_time=make_monday_9am())

        status = timer.get_status(current_time=make_monday_10am())
        assert status.estimated_deadline.weekday() != 5
        assert status.estimated_deadline.weekday() != 6
        assert status.estimated_deadline.date() not in holidays


class TestSlaTimerDeadlineAfterPauseResume:
    def test_single_pause_resume_then_expire_deadline_accuracy(self):
        timer = make_default_sla_timer(total_work_hours=4.0)
        timer.start(start_time=make_monday_9am())

        timer.pause(pause_time=make_monday_10am())
        timer.resume(resume_time=make_monday_11am())

        expected_deadline = timer.work_calendar.add_work_hours(make_monday_11am(), 3.0)

        status = timer.get_status(current_time=expected_deadline)
        assert status.is_expired is True
        assert status.elapsed_work_hours == 4.0
        assert status.estimated_deadline == expected_deadline

    def test_pause_resume_expire_deadline_matches_calculation(self):
        timer = make_default_sla_timer(total_work_hours=6.0)
        timer.start(start_time=make_monday_9am())

        timer.pause(pause_time=make_monday_10am())
        timer.resume(resume_time=make_monday_12pm())

        expected_deadline = timer.work_calendar.add_work_hours(make_monday_12pm(), 5.0)

        status = timer.get_status(current_time=expected_deadline)
        assert status.is_expired is True
        assert status.elapsed_work_hours == 6.0
        assert status.estimated_deadline == expected_deadline

    def test_multiple_pause_resume_deadline_accuracy(self):
        timer = make_default_sla_timer(total_work_hours=8.0)
        timer.start(start_time=make_monday_9am())

        timer.pause(pause_time=make_monday_10am())
        timer.resume(resume_time=make_monday_11am())

        timer.pause(pause_time=make_monday_12pm())
        timer.resume(resume_time=make_monday_1pm())

        expected_deadline = timer.work_calendar.add_work_hours(make_monday_1pm(), 6.0)

        status = timer.get_status(current_time=expected_deadline)
        assert status.is_expired is True
        assert status.elapsed_work_hours == 8.0
        assert status.estimated_deadline == expected_deadline

    def test_pause_across_lunch_break_deadline(self):
        timer = make_default_sla_timer(total_work_hours=3.0)
        timer.start(start_time=make_monday_11am())

        timer.pause(pause_time=make_monday_12pm())
        timer.resume(resume_time=make_monday_1pm())

        expected_deadline = timer.work_calendar.add_work_hours(make_monday_1pm(), 2.0)

        status = timer.get_status(current_time=expected_deadline)
        assert status.is_expired is True
        assert status.elapsed_work_hours == 3.0
        assert status.estimated_deadline == expected_deadline

    def test_pause_across_weekend_deadline_accuracy(self):
        timer = make_default_sla_timer(total_work_hours=5.0)
        timer.start(start_time=make_monday_9am())

        timer.pause(pause_time=make_monday_10am())
        timer.resume(resume_time=make_monday_next_week_9am())

        expected_deadline = timer.work_calendar.add_work_hours(make_monday_next_week_9am(), 4.0)

        status = timer.get_status(current_time=expected_deadline)
        assert status.is_expired is True
        assert status.elapsed_work_hours == 5.0
        assert status.estimated_deadline == expected_deadline

    def test_long_pause_then_expire_deadline(self):
        timer = make_default_sla_timer(total_work_hours=4.0)
        timer.start(start_time=make_monday_9am())

        timer.pause(pause_time=make_monday_10am())

        one_year_later = datetime(2025, 1, 15, 9, 0, 0)
        timer.resume(resume_time=one_year_later)

        expected_deadline = timer.work_calendar.add_work_hours(one_year_later, 3.0)

        status = timer.get_status(current_time=expected_deadline)
        assert status.is_expired is True
        assert status.elapsed_work_hours == 4.0
        assert status.estimated_deadline == expected_deadline

    def test_pause_resume_crossing_multiple_days_deadline(self):
        timer = make_default_sla_timer(total_work_hours=10.0)
        timer.start(start_time=make_monday_9am())

        timer.pause(pause_time=make_monday_4pm())
        timer.resume(resume_time=make_tuesday_9am())

        expected_deadline = timer.work_calendar.add_work_hours(make_tuesday_9am(), 4.0)

        status = timer.get_status(current_time=expected_deadline)
        assert status.is_expired is True
        assert status.elapsed_work_hours == 10.0
        assert status.estimated_deadline == expected_deadline

    def test_query_after_expired_with_pause_resume(self):
        timer = make_default_sla_timer(total_work_hours=4.0)
        timer.start(start_time=make_monday_9am())

        timer.pause(pause_time=make_monday_10am())
        timer.resume(resume_time=make_monday_11am())

        expected_deadline = timer.work_calendar.add_work_hours(make_monday_11am(), 3.0)

        query_time = expected_deadline + timedelta(days=5)
        status = timer.get_status(current_time=query_time)
        assert status.is_expired is True
        assert status.elapsed_work_hours == 4.0
        assert status.remaining_work_hours == 0.0
        assert status.estimated_deadline == expected_deadline

    def test_original_start_time_preserved_after_resume(self):
        timer = make_default_sla_timer(total_work_hours=5.0)
        original_start = make_monday_9am()
        timer.start(start_time=original_start)

        timer.pause(pause_time=make_monday_10am())
        timer.resume(resume_time=make_monday_11am())

        assert timer.start_time == original_start

    def test_deadline_calculation_uses_original_timeline(self):
        timer = make_default_sla_timer(total_work_hours=3.0)
        start_time = make_monday_9am()
        timer.start(start_time=start_time)

        timer.pause(pause_time=make_monday_10am())
        resume_time = make_tuesday_9am()
        timer.resume(resume_time=resume_time)

        expected_deadline = timer.work_calendar.add_work_hours(resume_time, 2.0)

        status_before = timer.get_status(current_time=resume_time)
        assert status_before.elapsed_work_hours == 1.0
        assert status_before.remaining_work_hours == 2.0
        assert status_before.estimated_deadline == expected_deadline

        status_after = timer.get_status(current_time=expected_deadline)
        assert status_after.is_expired is True
        assert status_after.estimated_deadline == expected_deadline
