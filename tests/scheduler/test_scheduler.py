from datetime import timedelta

import pytest

from solocoder_py.scheduler import (
    FairResourcePoolScheduler,
    InsufficientSlotsError,
    Priority,
    Task,
    TaskNotFoundError,
    TaskNotRunningError,
)

from tests.scheduler.conftest import FakeClock


class TestTaskModel:
    def test_task_create_assigns_id(self, make_task):
        task = make_task()
        assert task.id is not None
        assert len(task.id) > 0

    def test_task_default_priority(self, make_task):
        task = make_task()
        assert task.priority == Priority.NORMAL
        assert task.effective_priority == Priority.NORMAL

    def test_task_custom_priority(self, make_task):
        task = make_task(priority=Priority.HIGH)
        assert task.priority == Priority.HIGH
        assert task.effective_priority == Priority.HIGH

    def test_task_resource_slots_must_be_positive(self):
        with pytest.raises(ValueError, match="resource_slots must be positive"):
            Task(id="bad", resource_slots=0)
        with pytest.raises(ValueError, match="resource_slots must be positive"):
            Task(id="bad", resource_slots=-1)


class TestPriority:
    def test_priority_clamp_below_lowest(self):
        assert Priority.clamp(-100) == Priority.LOWEST

    def test_priority_clamp_above_highest(self):
        assert Priority.clamp(100) == Priority.HIGHEST

    def test_priority_clamp_within_range(self):
        assert Priority.clamp(2) == Priority.NORMAL

    def test_priority_int_ordering(self):
        assert Priority.LOWEST < Priority.LOW < Priority.NORMAL < Priority.HIGH < Priority.HIGHEST


class TestSchedulerSubmission:
    def test_submit_immediately_allocates_when_slots_available(self, make_scheduler, make_task):
        scheduler = make_scheduler(total_slots=5)
        task = make_task(resource_slots=2)

        result = scheduler.submit(task)

        assert result is task
        assert task.is_running is True
        assert task.started_at is not None
        assert scheduler.used_slots == 2
        assert scheduler.available_slots == 3
        assert scheduler.running_count == 1
        assert scheduler.waiting_count == 0

    def test_submit_queues_when_insufficient_slots(self, make_scheduler, make_task):
        scheduler = make_scheduler(total_slots=5)
        running = make_task(resource_slots=4)
        scheduler.submit(running)

        waiting = make_task(resource_slots=3)
        result = scheduler.submit(waiting)

        assert result is None
        assert waiting.is_running is False
        assert waiting.started_at is None
        assert scheduler.used_slots == 4
        assert scheduler.waiting_count == 1
        assert scheduler.running_count == 1

    def test_submit_rejects_task_larger_than_total_capacity(self, make_scheduler, make_task):
        scheduler = make_scheduler(total_slots=5)
        huge = make_task(resource_slots=10)

        with pytest.raises(InsufficientSlotsError):
            scheduler.submit(huge)

    def test_submit_resets_task_state(self, make_scheduler, make_task, fake_clock):
        scheduler = make_scheduler(total_slots=10)
        task = make_task(resource_slots=1)
        task.is_running = True
        task.effective_priority = Priority.HIGHEST
        task.is_starvation_protected = True

        fake_clock.advance(timedelta(seconds=10))
        result = scheduler.submit(task)

        assert result is task
        assert task.is_running is True
        assert task.effective_priority == task.priority
        assert task.is_starvation_protected is False
        assert task.wait_started_at == fake_clock()


class TestPriorityScheduling:
    def test_higher_priority_scheduled_first(self, make_scheduler, make_task):
        scheduler = make_scheduler(total_slots=2)
        t1 = make_task(resource_slots=2, priority=Priority.NORMAL)
        scheduler.submit(t1)

        low = make_task(resource_slots=2, priority=Priority.LOW)
        high = make_task(resource_slots=2, priority=Priority.HIGH)
        scheduler.submit(low)
        scheduler.submit(high)

        assert scheduler.waiting_count == 2

        newly_started = scheduler.release(t1.id)

        assert len(newly_started) == 1
        assert newly_started[0].id == high.id
        assert high.is_running is True
        assert low.is_running is False

    def test_same_priority_fcfs(self, make_scheduler, make_task, fake_clock):
        scheduler = make_scheduler(total_slots=1)
        blocker = make_task(resource_slots=1)
        scheduler.submit(blocker)

        first = make_task(resource_slots=1, priority=Priority.NORMAL)
        fake_clock.advance(timedelta(seconds=1))
        second = make_task(resource_slots=1, priority=Priority.NORMAL)
        fake_clock.advance(timedelta(seconds=1))
        third = make_task(resource_slots=1, priority=Priority.NORMAL)

        scheduler.submit(first)
        scheduler.submit(second)
        scheduler.submit(third)

        newly_started = scheduler.release(blocker.id)
        assert newly_started[0].id == first.id

        newly_started = scheduler.release(first.id)
        assert newly_started[0].id == second.id

    def test_effective_priority_overrides_original(self, make_scheduler, make_task):
        scheduler = make_scheduler(total_slots=1)
        blocker = make_task(resource_slots=1)
        scheduler.submit(blocker)

        low_original = make_task(resource_slots=1, priority=Priority.LOW)
        high_original = make_task(resource_slots=1, priority=Priority.HIGH)

        scheduler.submit(low_original)
        scheduler.submit(high_original)

        low_original.effective_priority = Priority.HIGHEST

        newly_started = scheduler.release(blocker.id)
        assert newly_started[0].id == low_original.id


class TestSlotRelease:
    def test_release_returns_newly_started_tasks(self, make_scheduler, make_task):
        scheduler = make_scheduler(total_slots=3)
        running = make_task(resource_slots=3)
        scheduler.submit(running)

        waiter = make_task(resource_slots=2)
        scheduler.submit(waiter)

        started = scheduler.release(running.id)

        assert len(started) == 1
        assert started[0].id == waiter.id
        assert scheduler.used_slots == 2

    def test_release_chain_multiple_tasks(self, make_scheduler, make_task):
        scheduler = make_scheduler(total_slots=4)
        running = make_task(resource_slots=4)
        scheduler.submit(running)

        w1 = make_task(resource_slots=1)
        w2 = make_task(resource_slots=2)
        w3 = make_task(resource_slots=1)
        scheduler.submit(w1)
        scheduler.submit(w2)
        scheduler.submit(w3)

        started = scheduler.release(running.id)

        assert len(started) == 3
        assert scheduler.used_slots == 4
        assert scheduler.running_count == 3
        assert scheduler.waiting_count == 0

    def test_release_preserves_leftover_slots(self, make_scheduler, make_task):
        scheduler = make_scheduler(total_slots=5)
        running = make_task(resource_slots=5)
        scheduler.submit(running)

        small = make_task(resource_slots=2)
        scheduler.submit(small)

        scheduler.release(running.id)
        assert scheduler.available_slots == 3

    def test_release_unknown_task_raises(self, make_scheduler):
        scheduler = make_scheduler(total_slots=5)
        with pytest.raises(TaskNotFoundError):
            scheduler.release("nonexistent")


class TestEdgeCases:
    def test_single_slot_allocation(self, make_scheduler, make_task):
        scheduler = make_scheduler(total_slots=1)
        t1 = make_task(resource_slots=1)
        t2 = make_task(resource_slots=1)

        assert scheduler.submit(t1) is t1
        assert scheduler.submit(t2) is None
        assert scheduler.available_slots == 0
        assert scheduler.waiting_count == 1

        started = scheduler.release(t1.id)
        assert len(started) == 1
        assert started[0].id == t2.id
        assert t2.is_running is True

    def test_task_consumes_all_slots(self, make_scheduler, make_task):
        scheduler = make_scheduler(total_slots=10)
        big = make_task(resource_slots=10)
        scheduler.submit(big)

        assert scheduler.used_slots == 10
        assert scheduler.available_slots == 0

        small = make_task(resource_slots=1)
        assert scheduler.submit(small) is None

        scheduler.release(big.id)
        assert small.is_running is True

    def test_exact_fit_after_release(self, make_scheduler, make_task):
        scheduler = make_scheduler(total_slots=5)
        a = make_task(resource_slots=2)
        b = make_task(resource_slots=2)
        scheduler.submit(a)
        scheduler.submit(b)
        assert scheduler.available_slots == 1

        need3 = make_task(resource_slots=3)
        scheduler.submit(need3)
        assert need3.is_running is False

        scheduler.release(a.id)
        assert need3.is_running is True
        assert scheduler.used_slots == 5

    def test_no_tasks_waiting_after_release(self, make_scheduler, make_task):
        scheduler = make_scheduler(total_slots=5)
        task = make_task(resource_slots=2)
        scheduler.submit(task)

        started = scheduler.release(task.id)
        assert started == []
        assert scheduler.used_slots == 0
        assert scheduler.running_count == 0

    def test_scheduler_rejects_non_positive_slots(self):
        with pytest.raises(ValueError, match="total_slots must be positive"):
            FairResourcePoolScheduler(total_slots=0)
        with pytest.raises(ValueError, match="total_slots must be positive"):
            FairResourcePoolScheduler(total_slots=-1)


class TestPriorityAging:
    def test_aging_promotes_after_interval(self, make_scheduler, make_task, fake_clock):
        scheduler = make_scheduler(
            total_slots=1,
            aging_interval=timedelta(seconds=30),
            aging_promotion_step=1,
            aging_threshold=Priority.LOW,
        )
        blocker = make_task(resource_slots=1)
        scheduler.submit(blocker)

        low_task = make_task(resource_slots=1, priority=Priority.LOW)
        scheduler.submit(low_task)
        original_effective = low_task.effective_priority

        fake_clock.advance(timedelta(seconds=29))
        scheduler.tick()
        assert low_task.effective_priority == original_effective

        fake_clock.advance(timedelta(seconds=1))
        scheduler.tick()
        assert low_task.effective_priority > original_effective
        assert low_task.last_promoted_at == fake_clock()

    def test_aged_priority_wins_over_waiting_higher_original(self, make_scheduler, make_task, fake_clock):
        scheduler = make_scheduler(
            total_slots=1,
            aging_interval=timedelta(seconds=10),
            aging_promotion_step=3,
            aging_threshold=Priority.LOW,
        )
        blocker = make_task(resource_slots=1)
        scheduler.submit(blocker)

        aged = make_task(resource_slots=1, priority=Priority.LOWEST)
        scheduler.submit(aged)

        fake_clock.advance(timedelta(seconds=14))
        higher_original = make_task(resource_slots=1, priority=Priority.HIGH)
        scheduler.submit(higher_original)

        fake_clock.advance(timedelta(seconds=1))
        scheduler.tick()

        assert aged.effective_priority >= Priority.HIGH
        assert higher_original.effective_priority == Priority.HIGH

        newly_started = scheduler.release(blocker.id)
        assert newly_started[0].id == aged.id

    def test_aging_does_not_exceed_highest(self, make_scheduler, make_task, fake_clock):
        scheduler = make_scheduler(
            total_slots=1,
            aging_interval=timedelta(seconds=1),
            aging_promotion_step=10,
            aging_threshold=Priority.LOW,
        )
        blocker = make_task(resource_slots=1)
        scheduler.submit(blocker)

        task = make_task(resource_slots=1, priority=Priority.LOWEST)
        scheduler.submit(task)

        fake_clock.advance(timedelta(seconds=5))
        scheduler.tick()
        assert task.effective_priority == Priority.HIGHEST

    def test_aging_resets_reference_after_promotion(self, make_scheduler, make_task, fake_clock):
        scheduler = make_scheduler(
            total_slots=1,
            aging_interval=timedelta(seconds=10),
            aging_promotion_step=1,
            aging_threshold=Priority.LOW,
        )
        blocker = make_task(resource_slots=1)
        scheduler.submit(blocker)

        task = make_task(resource_slots=1, priority=Priority.LOWEST)
        scheduler.submit(task)

        fake_clock.advance(timedelta(seconds=10))
        scheduler.tick()
        first_promotion_time = task.last_promoted_at
        first_effective = task.effective_priority

        fake_clock.advance(timedelta(seconds=5))
        scheduler.tick()
        assert task.last_promoted_at == first_promotion_time
        assert task.effective_priority == first_effective

        fake_clock.advance(timedelta(seconds=5))
        scheduler.tick()
        assert task.last_promoted_at > first_promotion_time
        assert task.effective_priority > first_effective


class TestStarvationProtection:
    def test_starvation_triggers_after_max_wait(self, make_scheduler, make_task, fake_clock):
        scheduler = make_scheduler(
            total_slots=1,
            aging_interval=timedelta(minutes=10),
            max_wait_time=timedelta(minutes=2),
        )
        blocker = make_task(resource_slots=1)
        scheduler.submit(blocker)

        task = make_task(resource_slots=1, priority=Priority.LOWEST)
        scheduler.submit(task)

        fake_clock.advance(timedelta(minutes=1, seconds=59))
        scheduler.tick()
        assert task.is_starvation_protected is False
        assert task.effective_priority == Priority.LOWEST

        fake_clock.advance(timedelta(seconds=1))
        scheduler.tick()
        assert task.is_starvation_protected is True
        assert task.effective_priority == Priority.HIGHEST

    def test_starvation_protected_tasks_go_first(self, make_scheduler, make_task, fake_clock):
        scheduler = make_scheduler(
            total_slots=1,
            max_wait_time=timedelta(minutes=1),
        )
        blocker = make_task(resource_slots=1)
        scheduler.submit(blocker)

        starved = make_task(resource_slots=1, priority=Priority.LOWEST)
        scheduler.submit(starved)

        very_high = make_task(resource_slots=1, priority=Priority.HIGHEST)
        scheduler.submit(very_high)

        fake_clock.advance(timedelta(minutes=2))
        scheduler.tick()

        newly_started = scheduler.release(blocker.id)
        assert newly_started[0].id == starved.id
        assert very_high.is_running is False

    def test_starvation_protected_fcfs_order(self, make_scheduler, make_task, fake_clock):
        scheduler = make_scheduler(
            total_slots=1,
            max_wait_time=timedelta(minutes=1),
        )
        blocker = make_task(resource_slots=1)
        scheduler.submit(blocker)

        first = make_task(resource_slots=1, priority=Priority.LOWEST)
        scheduler.submit(first)
        fake_clock.advance(timedelta(seconds=30))
        second = make_task(resource_slots=1, priority=Priority.LOWEST)
        scheduler.submit(second)

        fake_clock.advance(timedelta(minutes=2))
        scheduler.tick()

        assert first.is_starvation_protected is True
        assert second.is_starvation_protected is True

        newly_started = scheduler.release(blocker.id)
        assert newly_started[0].id == first.id


class TestInsufficientCapacityRejection:
    def test_task_larger_than_pool_rejected(self, make_scheduler, make_task):
        scheduler = make_scheduler(total_slots=5)
        task = make_task(resource_slots=6)
        with pytest.raises(InsufficientSlotsError):
            scheduler.submit(task)

    def test_task_exactly_fits_pool(self, make_scheduler, make_task):
        scheduler = make_scheduler(total_slots=5)
        task = make_task(resource_slots=5)
        result = scheduler.submit(task)
        assert result is task
        assert scheduler.used_slots == 5


class TestFullScenario:
    def test_aging_starvation_release_integration(
        self, make_scheduler, make_task, fake_clock
    ):
        scheduler = make_scheduler(
            total_slots=4,
            aging_interval=timedelta(minutes=2),
            aging_promotion_step=1,
            aging_threshold=Priority.LOW,
            max_wait_time=timedelta(minutes=5),
        )

        big = make_task(resource_slots=4, priority=Priority.NORMAL, name="big")
        scheduler.submit(big)

        starve_candidate = make_task(resource_slots=2, priority=Priority.LOWEST, name="starve")
        scheduler.submit(starve_candidate)

        fake_clock.advance(timedelta(minutes=3))
        age_candidate = make_task(resource_slots=1, priority=Priority.LOW, name="age")
        normal = make_task(resource_slots=1, priority=Priority.NORMAL, name="normal")
        scheduler.submit(age_candidate)
        scheduler.submit(normal)

        fake_clock.advance(timedelta(minutes=1, seconds=50))
        high = make_task(resource_slots=1, priority=Priority.HIGH, name="high")
        scheduler.submit(high)

        fake_clock.advance(timedelta(minutes=0, seconds=25))
        scheduler.tick()

        assert starve_candidate.is_starvation_protected is True
        assert starve_candidate.effective_priority == Priority.HIGHEST
        assert age_candidate.is_starvation_protected is False
        assert age_candidate.effective_priority >= Priority.NORMAL
        assert normal.is_starvation_protected is False
        assert high.is_starvation_protected is False

        started = scheduler.release(big.id)

        started_ids = {t.id for t in started}
        assert starve_candidate.id in started_ids
        assert high.id in started_ids
        assert scheduler.used_slots <= 4


class TestReleaseEdgeCases:
    def test_release_non_running_task(self, make_scheduler, make_task):
        scheduler = make_scheduler(total_slots=5)
        task = make_task(resource_slots=1)
        scheduler._running_tasks[task.id] = task
        task.is_running = False

        with pytest.raises(TaskNotRunningError):
            scheduler.release(task.id)


class TestHeadOfLineBlocking:
    def test_skip_large_task_and_allocate_smaller_one(self, make_scheduler, make_task):
        scheduler = make_scheduler(total_slots=5)

        a = make_task(resource_slots=4, priority=Priority.HIGH, name="A")
        filler = make_task(resource_slots=1, priority=Priority.HIGH, name="filler")
        scheduler.submit(a)
        scheduler.submit(filler)
        assert scheduler.used_slots == 5

        b = make_task(resource_slots=3, priority=Priority.HIGH, name="B")
        c = make_task(resource_slots=1, priority=Priority.NORMAL, name="C")
        scheduler.submit(b)
        scheduler.submit(c)

        assert b.is_running is False
        assert c.is_running is False
        assert scheduler.waiting_count == 2

        started = scheduler.release(filler.id)
        assert scheduler.used_slots == 4 + 1 == 5

        started_ids = {t.id for t in started}
        assert c.id in started_ids
        assert b.id not in started_ids
        assert c.is_running is True
        assert b.is_running is False
        assert scheduler.waiting_count == 1

    def test_multiple_skips_then_fill(self, make_scheduler, make_task):
        scheduler = make_scheduler(total_slots=10)

        big = make_task(resource_slots=7, priority=Priority.HIGH, name="big")
        small_running = make_task(resource_slots=2, priority=Priority.HIGH, name="small_running")
        scheduler.submit(big)
        scheduler.submit(small_running)
        assert scheduler.used_slots == 9

        huge = make_task(resource_slots=6, priority=Priority.HIGHEST, name="huge")
        greedy = make_task(resource_slots=5, priority=Priority.HIGH, name="greedy")
        medium = make_task(resource_slots=4, priority=Priority.HIGH, name="medium")
        small = make_task(resource_slots=2, priority=Priority.NORMAL, name="small")

        scheduler.submit(huge)
        scheduler.submit(greedy)
        scheduler.submit(medium)
        scheduler.submit(small)
        assert scheduler.waiting_count == 4

        started = scheduler.release(small_running.id)

        started_ids = {t.id for t in started}
        assert huge.id not in started_ids
        assert greedy.id not in started_ids
        assert medium.id not in started_ids
        assert small.id in started_ids
        assert small.is_running is True
        assert scheduler.used_slots == 7 + 2 == 9

    def test_head_block_starvation_then_normal_queued(self, make_scheduler, make_task, fake_clock):
        scheduler = make_scheduler(
            total_slots=5,
            max_wait_time=timedelta(minutes=1),
        )

        a = make_task(resource_slots=4)
        filler = make_task(resource_slots=1)
        scheduler.submit(a)
        scheduler.submit(filler)

        greedy_starved = make_task(resource_slots=4, priority=Priority.LOWEST, name="greedy")
        small = make_task(resource_slots=1, priority=Priority.NORMAL, name="small")
        scheduler.submit(greedy_starved)
        scheduler.submit(small)
        assert scheduler.waiting_count == 2

        fake_clock.advance(timedelta(minutes=2))
        scheduler.tick()

        assert greedy_starved.is_starvation_protected is True

        started = scheduler.release(a.id)

        started_ids = {t.id for t in started}
        assert greedy_starved.id in started_ids
        assert small.id not in started_ids

        scheduler.release(greedy_starved.id)
        assert small.is_running is True


class TestSubmitResetsState:
    def test_submit_resets_last_promoted_at(self, make_scheduler, make_task, fake_clock):
        scheduler = make_scheduler(
            total_slots=1,
            aging_interval=timedelta(seconds=10),
        )

        blocker = make_task(resource_slots=1)
        scheduler.submit(blocker)

        task = make_task(resource_slots=1, priority=Priority.LOWEST)
        scheduler.submit(task)

        fake_clock.advance(timedelta(seconds=15))
        scheduler.tick()
        assert task.last_promoted_at is not None

        scheduler.release(blocker.id)
        scheduler.release(task.id)

        assert task.last_promoted_at is not None

        scheduler.submit(task)
        assert task.last_promoted_at is None

    def test_resubmitted_task_ages_from_new_wait_start(self, make_scheduler, make_task, fake_clock):
        scheduler = make_scheduler(
            total_slots=1,
            aging_interval=timedelta(seconds=30),
            aging_threshold=Priority.LOW,
        )

        blocker1 = make_task(resource_slots=1)
        scheduler.submit(blocker1)

        task = make_task(resource_slots=1, priority=Priority.LOWEST)
        scheduler.submit(task)

        fake_clock.advance(timedelta(seconds=45))
        scheduler.tick()
        aged_priority = task.effective_priority
        assert aged_priority > Priority.LOWEST
        assert task.last_promoted_at is not None

        scheduler.release(blocker1.id)
        scheduler.release(task.id)

        blocker2 = make_task(resource_slots=1)
        scheduler.submit(blocker2)
        scheduler.submit(task)

        assert task.effective_priority == Priority.LOWEST
        assert task.last_promoted_at is None

        fake_clock.advance(timedelta(seconds=29))
        scheduler.tick()
        assert task.effective_priority == Priority.LOWEST
        assert task.last_promoted_at is None


class TestAgingStarvationInteraction:
    def test_aging_does_not_override_starvation_protection(self, make_scheduler, make_task, fake_clock):
        scheduler = make_scheduler(
            total_slots=1,
            aging_interval=timedelta(seconds=10),
            aging_promotion_step=1,
            aging_threshold=Priority.LOW,
            max_wait_time=timedelta(minutes=1),
        )
        blocker = make_task(resource_slots=1)
        scheduler.submit(blocker)

        task = make_task(resource_slots=1, priority=Priority.LOWEST)
        scheduler.submit(task)

        fake_clock.advance(timedelta(minutes=2))
        scheduler.tick()

        assert task.is_starvation_protected is True
        assert task.effective_priority == Priority.HIGHEST

        scheduler.tick()
        assert task.is_starvation_protected is True
        assert task.effective_priority == Priority.HIGHEST

    def test_starvation_supersedes_prior_aging(self, make_scheduler, make_task, fake_clock):
        scheduler = make_scheduler(
            total_slots=1,
            aging_interval=timedelta(seconds=15),
            aging_promotion_step=1,
            aging_threshold=Priority.LOW,
            max_wait_time=timedelta(minutes=1),
        )
        blocker = make_task(resource_slots=1)
        scheduler.submit(blocker)

        task = make_task(resource_slots=1, priority=Priority.LOWEST)
        scheduler.submit(task)

        fake_clock.advance(timedelta(seconds=45))
        scheduler.tick()
        assert task.is_starvation_protected is False
        assert Priority.LOWEST < task.effective_priority <= Priority.HIGHEST

        fake_clock.advance(timedelta(minutes=1))
        scheduler.tick()
        assert task.is_starvation_protected is True
        assert task.effective_priority == Priority.HIGHEST

    def test_starved_task_not_touched_by_aging(self, make_scheduler, make_task, fake_clock):
        scheduler = make_scheduler(
            total_slots=1,
            aging_interval=timedelta(seconds=5),
            max_wait_time=timedelta(minutes=1),
        )
        blocker = make_task(resource_slots=1)
        scheduler.submit(blocker)

        task = make_task(resource_slots=1, priority=Priority.LOWEST)
        scheduler.submit(task)

        fake_clock.advance(timedelta(minutes=2))
        scheduler.tick()

        promoted_at = task.last_promoted_at
        assert task.is_starvation_protected is True

        fake_clock.advance(timedelta(seconds=30))
        scheduler.tick()

        assert task.last_promoted_at == promoted_at
        assert task.effective_priority == Priority.HIGHEST
