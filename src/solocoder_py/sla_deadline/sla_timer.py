from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, time
from typing import Iterator, List, Optional, Tuple

from solocoder_py.work_calendar import WorkCalendar

from .exceptions import (
    InvalidSlaDurationError,
    InvalidWorkCalendarError,
    SlaTimerAlreadyStartedError,
    SlaTimerError,
    SlaTimerExpiredError,
    SlaTimerNotPausedError,
    SlaTimerNotRunningError,
    SlaTimerNotStartedError,
    SlaTimerStateError,
)
from .models import PauseRecord, SlaTimerResult, SlaTimerStatus


@dataclass
class SlaTimer:
    total_work_hours: float
    work_calendar: WorkCalendar = field(default_factory=WorkCalendar)
    _status: SlaTimerStatus = SlaTimerStatus.NOT_STARTED
    _start_time: Optional[datetime] = None
    _pause_records: List[PauseRecord] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.total_work_hours <= 0:
            raise InvalidSlaDurationError("SLA total work hours must be positive")
        if not isinstance(self.work_calendar, WorkCalendar):
            raise InvalidWorkCalendarError("Invalid work calendar instance")

    @property
    def status(self) -> SlaTimerStatus:
        return self._status

    @property
    def start_time(self) -> Optional[datetime]:
        return self._start_time

    @property
    def pause_records(self) -> List[PauseRecord]:
        return self._pause_records.copy()

    @property
    def is_running(self) -> bool:
        return self._status == SlaTimerStatus.RUNNING

    @property
    def is_paused(self) -> bool:
        return self._status == SlaTimerStatus.PAUSED

    @property
    def is_expired(self) -> bool:
        return self._status == SlaTimerStatus.EXPIRED

    @property
    def is_started(self) -> bool:
        return self._status != SlaTimerStatus.NOT_STARTED

    def start(self, start_time: Optional[datetime] = None) -> None:
        if self._status != SlaTimerStatus.NOT_STARTED:
            raise SlaTimerAlreadyStartedError("SLA timer has already been started")

        current_time = start_time or datetime.now()
        self._start_time = current_time
        self._status = SlaTimerStatus.RUNNING
        self._pause_records = []

        self._check_expiration(current_time)

    def pause(self, pause_time: Optional[datetime] = None) -> None:
        if self._status == SlaTimerStatus.NOT_STARTED:
            raise SlaTimerNotStartedError("SLA timer has not been started")
        if self._status == SlaTimerStatus.EXPIRED:
            raise SlaTimerExpiredError("SLA timer has expired")
        if self._status == SlaTimerStatus.PAUSED:
            raise SlaTimerNotRunningError("SLA timer is already paused")

        current_time = pause_time or datetime.now()
        self._check_expiration(current_time)

        if self._status == SlaTimerStatus.EXPIRED:
            raise SlaTimerExpiredError("SLA timer has expired")

        elapsed_before_pause = self._calculate_elapsed_work_hours(current_time)

        pause_record = PauseRecord(
            pause_time=current_time,
            work_hours_before_pause=elapsed_before_pause,
        )
        self._pause_records.append(pause_record)
        self._status = SlaTimerStatus.PAUSED

    def resume(self, resume_time: Optional[datetime] = None) -> None:
        if self._status == SlaTimerStatus.NOT_STARTED:
            raise SlaTimerNotStartedError("SLA timer has not been started")
        if self._status != SlaTimerStatus.PAUSED:
            if self._status == SlaTimerStatus.EXPIRED:
                raise SlaTimerExpiredError("SLA timer has expired")
            raise SlaTimerNotPausedError("SLA timer is not paused")

        current_time = resume_time or datetime.now()

        self._check_expiration(current_time)
        if self._status == SlaTimerStatus.EXPIRED:
            raise SlaTimerExpiredError("SLA timer has expired")

        if self._pause_records and self._pause_records[-1].is_active:
            self._pause_records[-1].resume_time = current_time

        self._status = SlaTimerStatus.RUNNING

    def get_status(self, current_time: Optional[datetime] = None) -> SlaTimerResult:
        if self._status == SlaTimerStatus.NOT_STARTED:
            raise SlaTimerNotStartedError("SLA timer has not been started")

        now = current_time or datetime.now()

        self._check_expiration(now)

        elapsed = self._calculate_elapsed_work_hours(now)
        remaining = max(0.0, self.total_work_hours - elapsed)

        if elapsed >= self.total_work_hours:
            self._status = SlaTimerStatus.EXPIRED

        if self._status == SlaTimerStatus.EXPIRED:
            deadline = self._calculate_actual_deadline()
        else:
            deadline = self.work_calendar.add_work_hours(now, remaining)

        return SlaTimerResult(
            total_work_hours=self.total_work_hours,
            elapsed_work_hours=min(elapsed, self.total_work_hours),
            remaining_work_hours=remaining,
            estimated_deadline=deadline,
            is_expired=self._status == SlaTimerStatus.EXPIRED,
            status=self._status,
            current_time=now,
        )

    def _build_timeline(self) -> list[tuple[datetime, str]]:
        if self._start_time is None:
            raise SlaTimerNotStartedError("SLA timer has not been started")

        timeline: list[tuple[datetime, str]] = [(self._start_time, 'start')]
        for record in self._pause_records:
            timeline.append((record.pause_time, 'pause'))
            if record.resume_time is not None:
                timeline.append((record.resume_time, 'resume'))

        timeline.sort(key=lambda x: x[0])
        return timeline

    def _iter_running_segments(
        self,
        timeline: list[tuple[datetime, str]],
        end_time: Optional[datetime] = None,
    ) -> Iterator[Tuple[datetime, Optional[datetime]]]:
        current_time = timeline[0][0]
        is_running = True

        for event_time, event_type in timeline[1:]:
            if end_time is not None and event_time > end_time:
                if is_running and current_time < end_time:
                    yield (current_time, end_time)
                return

            if event_time <= current_time:
                if event_type == 'pause':
                    is_running = False
                elif event_type == 'resume':
                    is_running = True
                continue

            if is_running:
                yield (current_time, event_time)

            current_time = event_time

            if event_type == 'pause':
                is_running = False
            elif event_type == 'resume':
                is_running = True

        if end_time is not None:
            if is_running and current_time < end_time:
                yield (current_time, end_time)
        else:
            if is_running:
                yield (current_time, None)

    def _calculate_actual_deadline(self) -> datetime:
        timeline = self._build_timeline()

        remaining_hours = self.total_work_hours

        for segment_start, segment_end in self._iter_running_segments(timeline):
            if segment_end is None:
                return self.work_calendar.add_work_hours(segment_start, remaining_hours)

            hours_available = self._calculate_work_hours_between(segment_start, segment_end)
            if hours_available >= remaining_hours:
                return self.work_calendar.add_work_hours(segment_start, remaining_hours)
            remaining_hours -= hours_available

        raise SlaTimerStateError(
            "Deadline calculation exhausted all running segments without locating the "
            "expiration point for an SLA marked EXPIRED. This indicates a state "
            "inconsistency: the elapsed duration should have reached total_work_hours "
            "but the reconstructed timeline does not account for sufficient work hours."
        )

    def _get_last_resume_time(self) -> Optional[datetime]:
        last_resume_time = None
        for record in reversed(self._pause_records):
            if record.resume_time is not None:
                last_resume_time = record.resume_time
                break
        return last_resume_time

    def _get_effective_start_time(self) -> datetime:
        if self._start_time is None:
            raise SlaTimerNotStartedError("SLA timer has not been started")

        last_resume_time = self._get_last_resume_time()
        if last_resume_time is not None:
            return last_resume_time
        return self._start_time

    def _get_accumulated_hours_before(self, target_time: datetime) -> float:
        timeline = self._build_timeline()

        total_hours = 0.0
        for segment_start, segment_end in self._iter_running_segments(timeline, end_time=target_time):
            total_hours += self._calculate_work_hours_between(segment_start, segment_end)

        return min(total_hours, self.total_work_hours)

    def _calculate_elapsed_work_hours(self, current_time: datetime) -> float:
        if self._status == SlaTimerStatus.NOT_STARTED:
            return 0.0

        if self._status == SlaTimerStatus.EXPIRED:
            return self.total_work_hours

        if self._status == SlaTimerStatus.PAUSED:
            if self._pause_records:
                return self._pause_records[-1].work_hours_before_pause
            return 0.0

        return self._get_accumulated_hours_before(current_time)

    def _calculate_work_hours_between(self, start: datetime, end: datetime) -> float:
        if end <= start:
            return 0.0

        schedule = self.work_calendar.config.work_schedule
        total_hours = 0.0
        current_dt = start

        while current_dt < end:
            current_date = current_dt.date()

            if not self.work_calendar.is_workday(current_date):
                current_dt = datetime.combine(current_date + timedelta(days=1), time(0, 0))
                continue

            work_periods = schedule.get_work_periods()
            found_period = False

            for period in work_periods:
                period_start_dt = datetime.combine(current_date, period.start)
                period_end_dt = datetime.combine(current_date, period.end)

                effective_start = max(current_dt, period_start_dt)
                effective_end = min(end, period_end_dt)

                if effective_start >= effective_end:
                    continue

                found_period = True
                duration_hours = (effective_end - effective_start).total_seconds() / 3600.0
                total_hours += duration_hours

                current_dt = effective_end

            if not found_period:
                current_dt = datetime.combine(current_date + timedelta(days=1), time(0, 0))

        return total_hours

    def _check_expiration(self, current_time: datetime) -> None:
        if self._status in (SlaTimerStatus.NOT_STARTED, SlaTimerStatus.EXPIRED):
            return

        elapsed = self._calculate_elapsed_work_hours(current_time)
        if elapsed >= self.total_work_hours:
            self._status = SlaTimerStatus.EXPIRED
